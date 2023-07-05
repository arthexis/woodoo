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
    )
    port = fields.Integer(
        string='Port', required=True, default=22,
    )

    # SSH credentials
    user = fields.Char(
        string='User', required=False,
    )
    password = fields.Char(
        string='Password', required=False,
    )
    private_pem_file = fields.Binary(
        string='Private PEM File', attachment=True, required=False,
    )
    private_pem_file_name = fields.Char(
        string='Private PEM File Name', required=False,
    )
    base_path = fields.Char(
        string='Base Path', required=False,
        default=lambda self: '/home/%s' % self.user,
    )

    # Applications
    application_ids = fields.One2many(
        string='Applications', comodel_name='datacenter.application',
        inverse_name='server_id',
    )

    # State
    state = fields.Selection(
        string='State', required=True,
        selection=[
            ('unknown', 'Unknown'),
            ('unreachable', 'Unreachable'),
            ('reachable', 'Reachable'),
            ('connected', 'Connected'),
        ],
        default='unknown',
    )

    # Get SSH connection
    def get_ssh_client(self):
        ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        if self.private_pem_file:
            private_pem_file_str = b64decode(self.private_pem_file).decode('utf-8')
            private_key = RSAKey.from_private_key(StringIO(private_pem_file_str))
            ssh_client.connect(
                hostname=self.host, port=self.port, username=self.user,
                pkey=private_key,
            )
        else:
            ssh_client.connect(
                hostname=self.host, port=self.port, username=self.user,
                password=self.password,
            )
        return ssh_client

    # Run command
    def run_command(self, command, cwd=None):
        ssh_client = self.get_ssh_client()
        if cwd:
            command = 'cd %s && %s' % (cwd, command)
        elif self.base_path:
            command = 'cd %s && %s' % (self.base_path, command)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        return self._format_output(stdout.read().decode())
    

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

    def run_command(self, command, cwd=None):
        # Iterpolate any variables in the command
        command = command % self._interpolate_variables()
        return self.server_id.run_command(command, cwd)

    def _interpolate_variables(self):
        return {
            'app_name': self.name,
            'app_port': self.app_port,
            'service_name': self.service_name,
        }

    def run_sql(self, query):
        return self.database_ids[0].run_sql(query)


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
