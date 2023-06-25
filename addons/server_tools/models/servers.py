from odoo import models, fields
from paramiko import SSHClient, AutoAddPolicy


class Server(models.Model):
    _name = 'server_tools.server'
    _description = 'Server'

    name = fields.Char(
        string='Name', required=True,
    )
    host = fields.Char(
        string='Host', required=True,
    )
    port = fields.Integer(
        string='Port', required=True, default=22,
    )
    user = fields.Char(
        string='User', required=False,
    )
    password = fields.Char(
        string='Password', required=False,
    )
    # Store PEM key as file upload
    pem_file = fields.Binary(
        string='PEM File', attachment=True)
    pem_file_name = fields.Char(
        string='PEM File Name'
    )
    application_ids = fields.One2many(
        string='Applications', comodel_name='server_tools.application',
        inverse_name='server_id',
    )

    # This field is used to store the last command executed on the server
    command = fields.Char(
        string='Command', required=False,
    )
    # Store command output as Text
    output = fields.Text(
        string='Output', required=False,
    )

    # Get SSH connection
    def get_ssh(self):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        if self.pem_key:
            ssh.connect(
                hostname=self.host, port=self.port, username=self.user,
                key_filename=self.pem_key.decode(),
            )
        else:
            ssh.connect(
                hostname=self.host, port=self.port, username=self.user,
                password=self.password,
            )
        return ssh

    # Run command
    def run_command(self, command=None):
        if not command:
            command = self.command
        ssh = self.get_ssh()
        stdin, stdout, stderr = ssh.exec_command(command)
        return stdout.read().decode()


class Application(models.Model):
    _name = 'server_tools.application'
    _description = 'Application'

    name = fields.Char(
        string='Name', required=True,
    )
    server_id = fields.Many2one(
        string='Server', comodel_name='server_tools.server',
    )
    user = fields.Char(
        string='User', required=True,
    )
    password = fields.Char(
        string='Password', required=True,
    )


class Database(models.Model):
    _name = 'server_tools.database'
    _description = 'Database'

    name = fields.Char(
        string='Name', required=True,
    )
    application_id = fields.Many2one(
        string='Application', comodel_name='server_tools.application',
    )
    ip_address = fields.Char(
        string='IP Address', required=True,
    )
    user = fields.Char(
        string='User', required=True,
    )
    password = fields.Char(
        string='Password', required=True,
    )

    # This field is used to store the last SQL query executed on the database
    sql = fields.Text(
        string='SQL', required=False,
    )

    # Run SQL query
    def run_sql(self, query=None):
        if not query:
            query = self.sql
        ssh = self.application_id.server_id.get_ssh()
        command = 'psql -h %s -U %s -d %s -c "%s"' % (
            self.ip_address, self.user, self.name, query,
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        return stdout.read().decode()

    