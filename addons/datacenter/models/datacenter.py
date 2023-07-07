from odoo import models, fields
from base64 import b64decode
from io import StringIO
from paramiko import SSHClient, AutoAddPolicy, RSAKey


# Datacenter models
    
class AppServer(models.Model):
    _name = 'datacenter.app.server'
    _description = 'App Server'

    name = fields.Char(string='Name', required=True)
    host = fields.Char(
        string='Host', required=True, track_visibility='always',
    )
    port = fields.Integer(
        string='Port', required=True, default=22,
        track_visibility='always'
    )

    # SSH credentials
    os_user = fields.Char(
        string='OS User', required=False, track_visibility='always', default='ubuntu',
    )
    private_pem_file = fields.Binary(
        string='Private PEM File', attachment=True, required=False,
        track_visibility='always',
    )
    private_pem_filename = fields.Char(
        string='Private PEM File Name', required=False,
        track_visibility='always',
    )

    # SSH settings
    base_path = fields.Char(
        string='Base Path', required=False,
        default=lambda self: '/home/%s' % self.user,
        track_visibility='always',
    )

    # Applications
    application_ids = fields.One2many(
        string='Applications', comodel_name='datacenter.application',
        inverse_name='server_id',
        track_visibility='always',
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
        track_visibility='always',
    )

    command = fields.Text(
        string='Command', required=False,
        default='echo "Hello World"',
        track_visibility='always',
    )

    # Output
    stdout = fields.Text(
        string='Stdout', required=False, readonly=True,
        track_visibility='always',
    )
    stderr = fields.Text(
        string='Stderr', required=False, readonly=True,
        track_visibility='always',
    )
    error_count = fields.Integer(
        string='Error Count', required=False, default=0, readonly=True,
    )

    # SSH connection
    def _get_ssh_client(self):
        ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        if self.private_pem_file:
            private_pem_file_str = b64decode(self.private_pem_file).decode('utf-8')
            private_key = RSAKey.from_private_key(StringIO(private_pem_file_str))
            ssh_client.connect(
                hostname=self.host, port=self.port, 
                username=self.user, pkey=private_key,
            )
        else:
            ssh_client.connect(
                hostname=self.host, port=self.port, 
                username=self.user, password=self.password,
            )
        return ssh_client

    # Run command
    def run_command(self, command=None, cwd=None, force=False, app_id=None):
        if self.state == 'pending' and not force:
            return 'Server is busy'
        if command:
            base_path = self.base_path if not app_id else self.application_ids.filtered(
                lambda x: x.id == app_id
            ).base_path
            if cwd:
                command = 'cd %s && %s' % (cwd, command)
            elif base_path:
                command = 'cd %s && %s' % (base_path, command)
            self.command = command
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
        track_visibility='always',
    )
    database_ids = fields.One2many(
        string='Databases', comodel_name='datacenter.app.database',
        inverse_name='application_id', track_visibility='always',
    )
    app_port = fields.Integer(
        string='App Port', required=False, default=80, track_visibility='always'
    )

    # Credentials
    admin_user = fields.Char(
        string='Admin User', required=False, track_visibility='always', default='admin',
    )
    admin_password = fields.Char(
        string='Admin Password', required=False, track_visibility='always'
    )

    # Configuration
    service_name = fields.Char(
        string='Service Name', required=False,
        default=lambda self: self.name,
        track_visibility='always',
    )
    base_path = fields.Char(
        string='Base Path', required=False,
        default=lambda self: '/home/%s' % self.user,
        track_visibility='always',
    )

    # State machine commands (7-step lifecycle)
    start_command = fields.Text(
        string='Start Command', required=False,
        default=lambda self: 'sudo systemctl start %s' % self.service_name,
        track_visibility='always',
    )
    stop_command = fields.Text(
        string='Stop Command', required=False,
        default=lambda self: 'sudo systemctl stop %s' % self.service_name,
        track_visibility='always',
    )
    restart_command = fields.Text(
        string='Restart Command', required=False,
        default=lambda self: 'sudo systemctl restart %s' % self.service_name,
        track_visibility='always',
    )
    status_command = fields.Text(
        string='Status Command', required=False,
        default=lambda self: 'sudo systemctl status %s' % self.service_name,
        track_visibility='always',
    )
    install_command = fields.Text(
        string='Install Command', required=False,
        default=lambda self: 'sudo apt-get install %s' % self.name,
        track_visibility='always',
    )
    update_command = fields.Text(
        string='Update Command', required=False,
        default=lambda self: 'sudo apt-get update && sudo apt-get upgrade',
        track_visibility='always',
    )
    uninstall_command = fields.Text(
        string='Uninstall Command', required=False,
        default=lambda self: 'sudo apt-get remove %s' % self.name,
        track_visibility='always',
    )

    def start(self):
        self.server_id.run_command(
            command=self.start_command, app_id=self.id,
        )
        self.server_id.flush()
    
    def stop(self):
        self.server_id.run_command(
            command=self.stop_command, app_id=self.id,
        )
        self.server_id.flush()

    def restart(self):
        self.server_id.run_command(
            command=self.restart_command, app_id=self.id,
        )
        self.server_id.flush()
        
    def status(self):
        return self.server_id.run_command(
            command=self.status_command, app_id=self.id,
        )
    
    def install(self):
        self.server_id.run_command(
            command=self.install_command, app_id=self.id,
        )
        self.server_id.flush()

    def update(self):
        self.server_id.run_command(
            command=self.update_command, app_id=self.id,
        )
        self.server_id.flush()

    def uninstall(self):
        self.server_id.run_command(
            command=self.uninstall_command, app_id=self.id,
        )
        self.server_id.flush()


class AppDatabase(models.Model):
    _name = 'datacenter.app.database'
    _description = 'Database'

    name = fields.Char(string='Name', required=True)
    application_id = fields.Many2one(
        string='Application', comodel_name='datacenter.application',
    )
    ip_address = fields.Char(string='IP Address', required=True)
    db_port = fields.Integer(string='DB Port', required=False, default=5432)

    # Credentials
    db_user = fields.Char(
        string='User', required=True,
        help='The DB user must have access without a password',
    )

    # Run SQL query
    def run_sql(self, query):
        ssh = self.application_id.server_id.get_ssh()
        command = 'psql -h %s -U %s -d %s -c "%s"' % (
            self.ip_address, self.db_user, self.name, query,
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        return stdout.read().decode()
