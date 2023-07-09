from odoo import models, fields, exceptions
from base64 import b64decode
from io import StringIO
from paramiko import SSHClient, AutoAddPolicy, RSAKey
from . import sigils


# Datacenter models
    
class AppServer(models.Model):
    _name = 'datacenter.app.server'
    _description = 'App Server'

    name = fields.Char(string='Name', required=True)
    host = fields.Char(
        string='Host IP', required=True,
        help='The IP address of the server',
    )
    ssh_port = fields.Integer(
        string='Port', required=True, default=22,
    )

    # SSH credentials
    os_user = fields.Char(
        string='OS User', required=False, default='ubuntu',
    )
    private_pem_file = fields.Binary(
        string='PEM File', attachment=True, required=False,
        help='The PEM file should contain the SSH private key',
    )
    private_pem_filename = fields.Char(
        string='PEM File Name', required=False,
    )

    # SSH settings
    base_path = fields.Char(
        string='Base Path', required=False,
        default=lambda self: '/home/%s' % self.os_user,
        help='The base path where all applications will be installed',
    )

    # Applications
    application_ids = fields.One2many(
        string='Applications', comodel_name='datacenter.application',
        inverse_name='server_id',
    )

    # State machine
    state = fields.Selection(
        string='State', required=True,
        selection=[
            ('unknown', 'Unknown'),
            ('failure', 'Failure'),
            ('success', 'Success'),
            ('pending', 'Pending'),
        ],
        default='unknown',
    )

    command = sigils.SigilText(
        string='Command', required=False,
        default='echo "%[host]"',
        sigil_info=True,
    )
    error_count = fields.Integer(
        string='Error Count', required=False, default=0, readonly=True,
    )

    # Output
    stdout = fields.Text(
        string='Stdout', required=False, readonly=True,
    )
    stderr = fields.Text(
        string='Stderr', required=False, readonly=True,
    )

    # Server scripts
    script_ids = fields.Many2many(
        string='Scripts', comodel_name='datacenter.script',
        relation='datacenter_script_server_rel',
    )

    # SSH connection
    def _get_ssh_client(self):
        ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        private_pem_file_str = b64decode(self.private_pem_file).decode('utf-8')
        if not private_pem_file_str:
            raise exceptions.ValidationError('Private PEM file is empty')
        private_key = RSAKey.from_private_key(StringIO(private_pem_file_str))
        ssh_client.connect(
            hostname=self.host, port=self.ssh_port, 
            username=self.os_user, pkey=private_key,
        )
        return ssh_client

    def upload(self, file_path, content=None, chmod_exec=False):
        if not content:
            content = self.command
        ssh_client = self._get_ssh_client()
        sftp_client = ssh_client.open_sftp()
        sftp_client.open(file_path, 'w').write(content)
        if chmod_exec:
            sftp_client.chmod(file_path, 0o755)
        sftp_client.close()
        return file_path

    # Show just the command after resolving variables
    def resolve(self, command=None):
        if not command:
            command = self.command
        try:
            return command % self
        except Exception as e:
            raise exceptions.ValidationError(str(e))

    # Run command
    def execute(self, command=None, base_path=None, force=False):
        if self.state == 'pending' and not force:
            return 'Server is busy'
        if command:
            if base_path:
                if not base_path.startswith('/'):
                    base_path = '%s/%s' % (self.base_path, base_path)
                command = 'cd %s && %s' % (base_path, command)
            elif self.base_path:
                command = 'cd %s && %s' % (self.base_path, command)
            self.command = self.resolve(command)
        else:
            command = self.command
        self.state = 'pending'
        self.stdout = None
        self.stderr = None
        # Save changes before running command
        self.flush()
        try:
            ssh_client = self._get_ssh_client()
            _, stdout, stderr = ssh_client.exec_command(command)
            # Get exit code and output
            self.stdout = stdout.read().decode()
            self.stderr = stderr.read().decode()
            self.state = 'success'
            self.error_count = 0
        except Exception as e:
            self.stderr = str(e)
            self.state = 'failure'
            self.error_count += 1
        self.flush()
        return self.stdout
    

class Application(models.Model):
    _name = 'datacenter.application'
    _description = 'Application'

    name = fields.Char(string='Name', required=True)
    server_id = fields.Many2one(
        string='Server', comodel_name='datacenter.app.server',
    )
    database_ids = fields.One2many(
        string='Databases', comodel_name='datacenter.app.database',
        inverse_name='application_id', 
    )

    # Configuration
    service_name = fields.Char(
        string='Service Name', required=True,
        default=lambda self: self.name,
    )
    base_path = fields.Char(
        string='Base Path', required=False,
        default=lambda self: '/home/%s/%s' % (self.server_id.os_user, self.service_name, ),
        help='The base path is where the application will be installed',
    )
    app_port = fields.Integer(
        string='App Port', required=False, default=80, 
    )
    virtual_env = fields.Char(
        string='Virtual Env', required=False,
        default=lambda self: '/home/%s/venv' % self.service_name,
    )

    # App Access
    base_url = fields.Char(
        string='Base URL', required=True, 
        default=lambda self: 'https://%s' % self.service_name,
    )
    admin_user = fields.Char(
        string='Admin User', required=False, default='admin',
    )
    admin_secret = fields.Char(
        string='Admin Secret', required=False, 
    )

    # Operations
    start_command = fields.Text(
        string='Start Command', required=False,
        default=lambda self: 'sudo systemctl start %s' % self.service_name,
    )
    stop_command = fields.Text(
        string='Stop Command', required=False,
        default=lambda self: 'sudo systemctl stop %s' % self.service_name,
    )
    restart_command = fields.Text(
        string='Restart Command', required=False,
        default=lambda self: 'sudo systemctl restart %s' % self.service_name,
    )
    status_command = fields.Text(
        string='Status Command', required=False,
        default=lambda self: 'sudo systemctl status %s' % self.service_name,
    )
    status_pattern = fields.Char(
        string='Status Pattern', required=False,
        default=lambda self: 'Active: active (running)',
    )

    # Lifecycle
    install_script = fields.Text(
        string='Install Script', required=False,
        default=lambda self: 'sudo apt-get install %s' % self.service_name,
    )
    update_script = fields.Text(
        string='Update Script', required=False,
        default=lambda self: 'sudo apt-get update && sudo apt-get upgrade',
    )
    uninstall_script = fields.Text(
        string='Uninstall Script', required=False,
        default=lambda self: 'sudo apt-get remove %s' % self.service_name,
    )

    # Expected status of the service
    expected_status = fields.Selection(
        string='Expected Status', required=True,
        selection=[
            ('running', 'Running'),
            ('stopped', 'Stopped'),
        ],
        default='stopped',
    )

    # App Scripts
    script_ids = fields.Many2many(
        string='Scripts', comodel_name='datacenter.script',
        relation='datacenter_script_application_rel',
    )

    # Operations (buttons)
    def start(self):
        self.expected_status = 'running'
        self.flush()
        self.server_id.execute(command=self.start_command)
    
    def stop(self):
        self.expected_status = 'stopped'
        self.flush()
        self.server_id.execute(command=self.stop_command)

    def restart(self):
        self.expected_status = 'running'
        self.flush()
        self.server_id.execute(command=self.restart_command)
        
    def status(self):
        result = self.server_id.execute(command=self.status_command)
        return 'running' if self.status_pattern in result else 'stopped'
    
    # Lifecycle (buttons)
    def install(self):
        if not self.server_id or not self.install_script:
            raise exceptions.ValidationError('Missing server or install script')
        filename = self.server_id.upload(
            content=self.install_script, 
            file_path='%s/install.sh' % self.base_path, chmod_exec=True,
        )
        self.server_id.execute(command=filename)

    def update(self):
        if not self.server_id or not self.update_script:
            raise exceptions.ValidationError('Missing server or update script')
        filename = self.server_id.upload(
            content=self.update_script, 
            file_path='%s/update.sh' % self.base_path, chmod_exec=True,
        )
        self.server_id.execute(command=filename)

    def uninstall(self):
        if not self.server_id or not self.uninstall_script:
            raise exceptions.ValidationError('Missing server or uninstall script') 
        filename = self.server_id.upload(
            content=self.uninstall_script, 
            file_path='%s/uninstall.sh' % self.base_path, chmod_exec=True,
        )
        self.server_id.execute(command=filename)

class AppDatabase(models.Model):
    _name = 'datacenter.app.database'
    _description = 'Database'

    name = fields.Char(string='Name', required=True)
    application_id = fields.Many2one(
        string='Application', comodel_name='datacenter.application',
    )
    ip_address = fields.Char(string='IP Address', required=True)
    db_name = fields.Char(string='DB Name', required=True)
    db_port = fields.Integer(string='DB Port', required=False, default=5432)

    # Credentials
    db_user = fields.Char(
        string='DB User', required=True,
        help='The DB user must have access without a password',
    )

    # Database scripts
    script_ids = fields.Many2many(
        string='Scripts', comodel_name='datacenter.script',
        relation='datacenter_script_database_rel',
    )


class Script(models.Model):
    _name = 'datacenter.script'
    _description = 'Script'

    name = fields.Char(string='Name', required=True)
    script = fields.Text(
        string='Script Content', required=True)
    filename = fields.Char(
        string='File Name', required=False,
        default=lambda self: '%s.sh' % self.name,
    )

    # Script dependencies
    dependency_ids = fields.Many2many(
        string='Dependencies', comodel_name='datacenter.script',
        relation='datacenter_script_dependency_rel',
        column1='script_id', column2='dependency_id',
    )

    def upload(self):
        self.server_id.upload(
            content=self.script, file_path=self.file_path, chmod_exec=True,
        )

    def run(self, force=False):
        self.upload()
        self.server_id.execute(command=self.file_path, force=force)

