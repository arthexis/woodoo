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
        string='Port', required=True,
    )
    user = fields.Char(
        string='User', required=True,
    )
    password = fields.Char(
        string='Password', required=True,
    )
    application_ids = fields.One2many(
        string='Applications', comodel_name='server_tools.application',
        inverse_name='server_id',
    )

    # Get SSH connection
    def get_ssh(self):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(
            hostname=self.host, port=self.port, username=self.user,
            password=self.password,
        )
        return ssh

    # Run command
    def run_command(self, command):
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
