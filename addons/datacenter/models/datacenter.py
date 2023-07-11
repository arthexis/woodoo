import re
from io import StringIO
from base64 import b64decode
from functools import reduce

from odoo import models, fields, exceptions
from paramiko import SSHClient, AutoAddPolicy, RSAKey
import psycopg2


def interpolate(text, data, depth=0, max_depth=20):
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



class DuplicateMixin(models.AbstractModel):
    _name = 'duplicate.mixin'
    _description = 'Mixin to duplicate records'

    def duplicate_record(self):
        for record in self:
            record.copy()



# Datacenter models

    
class AppServer(models.Model):
    _name = 'datacenter.app.server'
    _description = 'App Server'
    _inherit = ['duplicate.mixin']

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


class Application(models.Model):
    _name = 'datacenter.application'
    _description = 'Application'
    _inherit = ['duplicate.mixin']

    name = fields.Char(string='Name', required=True)
    app_code = fields.Char(
        string='App Code', required=False, unique=True,
        help='Unique identifier for the application',
    )

    server_id = fields.Many2one(
        string='Server', comodel_name='datacenter.app.server',
    )
    database_id = fields.Many2one(
        string='Database', comodel_name='datacenter.app.database',
    )

    # Configuration
    service_name = fields.Char(
        string='Service Name', required=True,
        default=lambda self: self.name,
        help='The service name is used for the systemd service unit',
    )
    base_path = fields.Char(
        string='Base Path', required=False,
        default=lambda self: '%[service_name]',
        help='The base path is where the application will be installed',
    )
    app_port = fields.Integer(
        string='App Port', required=False, default=80, 
    )

    # App Access
    base_url = fields.Char(
        string='Base URL', required=True, 
        default=lambda self: 'https://%[service_name]',
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
        default=lambda self: 'sudo systemctl start %[service_name]',
    )
    stop_command = fields.Text(
        string='Stop Command', required=False,
        default=lambda self: 'sudo systemctl stop %[service_name]',
    )
    restart_command = fields.Text(
        string='Restart Command', required=False,
        default=lambda self: 'sudo systemctl restart %[service_name]',
    )
    status_command = fields.Text(
        string='Status Command', required=False,
        default=lambda self: 'sudo systemctl status %[service_name]',
    )
    status_pattern = fields.Char(
        string='Status Pattern', required=False,
        default=lambda self: 'Active: active (running)',
    )
    journal_command = fields.Text(
        string='Journal Command', required=False,
        default=lambda self: 'sudo journalctl -u %[service_name] -n 30',
    )

    # Lifecycle
    install_script = fields.Text(
        string='Install Script', required=False,
    )
    update_script = fields.Text(
        string='Update Script', required=False,
    )
    uninstall_script = fields.Text(
        string='Uninstall Script', required=False,
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

    def _run_command(self, command, interpolate=True):
        if interpolate:
            command = interpolate(command, self)
        self.last_message = self.server_id.execute(
            command=command, base_path=self.base_path)

    # Operations (buttons)
    def start(self):
        self._expect_status('running')
        self._run_command(self.start_command)

    def stop(self):
        self._expect_status('stopped')
        self._run_command(self.stop_command)

    def restart(self):
        self._expect_status('running')
        self._run_command(self.restart_command)
        
    def status(self):
        command = interpolate(self.status_command, self)
        result = self.server_id.execute(
            command=command, base_path=self.base_path)
        status = 'running' if self.status_pattern in result else 'stopped'
        self.last_message = result
        self._expect_status(status)
        return status

    def journal(self):
        self._run_command(self.journal_command)

    def _run_as_script(self, content, filename, interpolate=True):
        if interpolate:
            content = interpolate(content, self)
        file_path = '%s/%s' % (self.base_path, filename)
        file_path = self.server_id.upload(
            content=content, file_path=file_path, chmod_exec=True)
        self.last_message = self.server_id.execute(
            command=file_path, base_path=self.base_path)
    
    # Lifecycle (buttons)
    def install(self):
        if not self.server_id or not self.install_script:
            raise exceptions.ValidationError('Missing server or install script')
        # Make sure the base path exists or the upload will fail
        self.server_id.execute(command='mkdir -p %s' % self.base_path)
        self._run_as_script(self.install_script, 'install.sh')

    def update(self):
        if not self.server_id or not self.update_script:
            raise exceptions.ValidationError('Missing server or update script')
        self._run_as_script(self.update_script, 'update.sh')

    def uninstall(self):
        # Check the server is stopped first
        if self.status() == 'running':
            raise exceptions.ValidationError('Application must be stopped first')
        if not self.server_id or not self.uninstall_script:
            raise exceptions.ValidationError('Missing server or uninstall script') 
        self._run_as_script(self.uninstall_script, 'uninstall.sh')


class AppDatabase(models.Model):
    _name = 'datacenter.app.database'
    _description = 'Database'
    _inherit = ['duplicate.mixin']

    name = fields.Char(string='Name', required=True)
    server_name = fields.Char(
        string='Server', required=True,
        help='Name of the Server where the database is installed',
    )
    application_ids = fields.One2many(
        string='Applications', comodel_name='datacenter.application',
        inverse_name='database_id',
    )
    ip_address = fields.Char(string='Endpoint', required=True)
    db_name = fields.Char(
        string='DB Name', required=True, 
        default=lambda self: self.name,
    )
    db_port = fields.Integer(string='DB Port', required=False, default=5432)

    # Credentials
    db_user = fields.Char(
        string='DB User', required=True,
        help='This DB user must have access without a password',
    )

    setup_script = fields.Text(
        string='Setup Script', required=False,
    )

    last_message = fields.Text(
        string='Last Message', required=False, readonly=True,
        default=lambda self: 'No messages',
    )

    def setup(self):
        if not self.setup_script:
            raise exceptions.ValidationError('Missing setup script')
        content = interpolate(self.setup_script, self)
        self._run_sql(content)

    def _run_sql(self, content):
        # Run the SQL using psycopg2
        conn = psycopg2.connect(
            host=self.ip_address, port=self.db_port, 
            user=self.db_user, database=self.db_name,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Split the content into separate commands
        commands = content.split(";")
        errors = []  # List to store any error messages
        for command in commands:
            command = command.strip()  # Remove leading/trailing whitespace
            if not command:  # Skip empty commands
                continue
            try:
                cur.execute(command)
            except Exception as e:
                errors.append(str(e))  # Add the error message to the list

        # If there were any errors, store them in last_message
        if errors:
            self.last_message = "\n".join(errors)
        else:
            self.last_message = str(cur.fetchall())

        conn.commit()
        cur.close()
        conn.close()

