from odoo import models, fields, exceptions
from base64 import b64decode
from io import StringIO
from paramiko import SSHClient, AutoAddPolicy, RSAKey
from functools import reduce
import re


def interpolate(text, data, depth=0, max_depth=8):
    cache = {}  # initialize the cache

    if depth > max_depth:
        return text

    pattern = r'%\[[\w\.]+\]'

    def replacement(match):
        token = match.group(0)  # include the %[ and ] in the token
        if token in cache:
            return cache[token]  # if the token is in the cache, return the cached result

        key = token[2:-1]  # remove the %[ and ] from the token
        try:
            if isinstance(data, dict):
                keys = key.split('.')
                value = reduce(dict.get, keys, data)
            else:
                value = getattr(data, key)
            if value is None:
                value = token  # if value is None, return the original token
            else:
                value = str(value)
        except AttributeError:
            value = token  # if an AttributeError is raised, return the original token

        cache[token] = value  # store the result in the cache
        return value

    interpolated = re.sub(pattern, replacement, text)

    if re.search(pattern, interpolated):
        return interpolate(interpolated, data, depth=depth+1, max_depth=max_depth)
    else:
        return interpolated


class MagicFieldMixin(models.AbstractModel):
    _name = 'datacenter.magic_field_mixin'
    _description = 'Magic Field Mixin'

    def write(self, values):
        for field_name, field in self._fields.items():
            if field.default and not self[field_name] and (field_name not in values or values[field_name] is None):
                values[field_name] = field.default(self)
        return super().write(values)


# Datacenter models

    
class AppServer(models.Model, MagicFieldMixin):
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

    command = fields.Text(
        string='Command', required=False,
        default='hostname',
        help='The last/next command to be executed on the server.',
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
            self.command = command
        else:
            command = self.command
        self.state = 'pending'
        self.stdout = None
        self.stderr = None
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


class Application(models.Model, MagicFieldMixin):
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
        string='Service', required=True,
        default=lambda self: self.name,
        help='The service name is used for the systemd service unit',
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
    journal_command = fields.Text(
        string='Journal Command', required=False,
        default=lambda self: 'sudo journalctl -u %s -n 30' % self.service_name,
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
    last_message = fields.Text(
        string='Last Message', required=False, readonly=True,
        default=lambda self: 'No messages',
    )

    def _expect_status(self, status):
        self.expected_status = status
        self.flush()

    # Operations (buttons)
    def start(self):
        self._expect_status('running')
        command = interpolate(self.start_command, self)
        self.last_message = self.server_id.execute(
            command=command, base_path=self.base_path)
    
    def stop(self):
        self._expect_status('stopped')
        command = interpolate(self.stop_command, self)
        self.last_message = self.server_id.execute(
            command=command, base_path=self.base_path)

    def restart(self):
        self._expect_status('running')
        command = interpolate(self.restart_command, self)
        self.last_message = self.server_id.execute(
            command=command, base_path=self.base_path)
        
    def status(self):
        command = interpolate(self.status_command, self)
        result = self.server_id.execute(
            command=command, base_path=self.base_path)
        status = 'running' if self.status_pattern in result else 'stopped'
        self.last_message = result
        self._expect_status(status)
        return status

    def journal(self):
        command = interpolate(self.journal_command, self)
        self.last_message = self.server_id.execute(
            command=command, base_path=self.base_path)
    
    # Lifecycle (buttons)
    def install(self):
        if not self.server_id or not self.install_script:
            raise exceptions.ValidationError('Missing server or install script')
        self.server_id.execute(
            command='mkdir -p %s' % self.base_path, base_path=None)
        content = interpolate(self.install_script, self)
        filename = self.server_id.upload(
            content=content,
            file_path='%s/install.sh' % self.base_path, 
            chmod_exec=True,
        )
        self.last_message = self.server_id.execute(
            command=filename, base_path=self.base_path)

    def update(self):
        if not self.server_id or not self.update_script:
            raise exceptions.ValidationError('Missing server or update script')
        content = interpolate(self.update_script, self)
        filename = self.server_id.upload(
            content=content, 
            file_path='%s/update.sh' % self.base_path, 
            chmod_exec=True,
        )
        self.last_message = self.server_id.execute(
            command=filename, base_path=self.base_path)

    def uninstall(self):
        # Check the server is stopped first
        if self.status() == 'running':
            raise exceptions.ValidationError('Application must be stopped first')
        if not self.server_id or not self.uninstall_script:
            raise exceptions.ValidationError('Missing server or uninstall script') 
        content = interpolate(self.uninstall_script, self)
        filename = self.server_id.upload(
            content=content,
            file_path='%s/uninstall.sh' % self.base_path, chmod_exec=True,
        )
        self.last_message = self.server_id.execute(
            command=filename, base_path=self.base_path)


class AppDatabase(models.Model, MagicFieldMixin):
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

