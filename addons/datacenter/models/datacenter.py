from odoo import models, fields
from base64 import b64decode
from io import StringIO
from paramiko import SSHClient, AutoAddPolicy, RSAKey


# Datacenter models
    
class AppServer(models.Model):
    _name = 'datacenter.app.server'
    _description = 'App Server'

    name = fields.Char(
        string='Name', required=True,
    )
    host = fields.Char(
        string='Host', required=True,
        track_visibility='always',
    )
    port = fields.Integer(
        string='Port', required=True, default=22,
        track_visibility='always'
    )

    # SSH credentials
    user = fields.Char(
        string='User', required=False,
        track_visibility='always',
    )
    password = fields.Char(
        string='Password', required=False,
        track_visibility='always',
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

    # State:
    # Treat each server as a state machine
    # This means each server can only be processing one command at a time
    # and prevents having the server in an unknown state.
    # If the server is in the 'pending' state, it means it is waiting for
    # a command to be run and new commands should not be accepted.

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

    original_command = fields.Text(
        string='Original Command', required=False,
        default='echo "Hello World"',
        track_visibility='always',
    )
    resolved_command = fields.Text(
        string='Resolved Command', required=False,
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

    # Get SSH connection
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

    def _interpolate_variables(self, command):
        # Interpolate variables
        # TODO: Add more variables
        return command

    # Run command
    # Set the state to 'pending' and run the command
    # Catch any errors, return the output and set the state to 
    # 'failure' or 'success' depending on the result

    def run_command(self, command=None, cwd=None):
        if self.state == 'pending':
            return 'Server is busy'
        if command:
            if cwd:
                command = 'cd %s && %s' % (cwd, command)
            elif self.base_path:
                command = 'cd %s && %s' % (self.base_path, command)
            self.original_command = command
        else:
            command = self.original_command
        self.state = 'pending'
        self.resolved_command = self._interpolate_variables(command)
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
        return self.stdout
    

class Application(models.Model):
    _name = 'datacenter.application'
    _description = 'Application'

    name = fields.Char(
        string='Name', required=True,
    )
    server_id = fields.Many2one(
        string='Server', comodel_name='datacenter.app.server',
    )
    database_ids = fields.One2many(
        string='Databases', comodel_name='datacenter.app.database',
        inverse_name='application_id',
    )
    app_port = fields.Integer(
        string='App Port', required=False, default=80,
    )

    # Credentials
    user = fields.Char(
        string='User', required=False,
    )
    password = fields.Char(
        string='Password', required=False,
    )

    # Configuration
    service_name = fields.Char(
        string='Service Name', required=False,
        default=lambda self: self.name,
    )


class AppDatabase(models.Model):
    _name = 'datacenter.app.database'
    _description = 'Database'

    name = fields.Char(
        string='Name', required=True,
    )
    application_id = fields.Many2one(
        string='Application', comodel_name='datacenter.application',
    )
    ip_address = fields.Char(
        string='IP Address', required=True,
    )
    db_port = fields.Integer(
        string='DB Port', required=False, default=5432,
    )

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
