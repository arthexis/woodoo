from odoo import models, fields
from base64 import b64decode
from io import StringIO
from paramiko import SSHClient, AutoAddPolicy, RSAKey


# Datacenter models


class CommandModel(models.Model):
    _name = 'datacenter.command_model'
    _description = 'Command Model'
    _abstract = True

    name = fields.Char(
        string='Name', required=True,
    )
    description = fields.Text(
        string='Description', required=False,
    )


class ServerModel(models.Model):
    _name = 'datacenter.server_model'
    _description = 'Server Model'
    _inherit = 'datacenter.command_model'

    server_ids = fields.One2many(
        string='Servers', comodel_name='datacenter.server',
        inverse_name='server_model_id',
    )
    

class Server(models.Model):
    _name = 'datacenter.server'
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

    # Behavior
    server_model_id = fields.Many2one(
        string='Server Model', comodel_name='datacenter.server_model',
    )

    # Get SSH connection
    def get_ssh(self):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        if self.private_pem_file:
            private_pem_file_str = b64decode(self.private_pem_file).decode('utf-8')
            private_key = RSAKey.from_private_key(StringIO(private_pem_file_str))
            ssh.connect(
                hostname=self.host, port=self.port, username=self.user,
                pkey=private_key,
            )
        else:
            ssh.connect(
                hostname=self.host, port=self.port, username=self.user,
                password=self.password,
            )
        return ssh

    # Run command
    def run_command(self, command):
        ssh = self.get_ssh()
        if self.base_path:
            command = 'cd %s && %s' % (self.base_path, command)
        stdin, stdout, stderr = ssh.exec_command(command)
        return self._format_output(stdout.read().decode())
    

class AppModel(models.Model):
    _name = 'datacenter.app_model'
    _description = 'App Model'
    _inherit = 'datacenter.command_model'
    
    app_ids = fields.One2many(
        string='Apps', comodel_name='datacenter.application',
        inverse_name='app_model_id',
    )

    # App Source
    git_url = fields.Char(
        string='Git URL', required=False,
    )
    git_branch = fields.Char(
        string='Git Branch', required=False,
    )

    # Installation
    requirements = fields.Char(
        string='Requirements', required=False,
        help='Comma separated list of requirements to install',
    )
    

class Application(models.Model):
    _name = 'datacenter.application'
    _description = 'Application'

    name = fields.Char(
        string='Name', required=True,
    )
    server_id = fields.Many2one(
        string='Server', comodel_name='datacenter.server',
    )
    app_port = fields.Integer(
        string='App Port', required=False, default=80,
    )

    # Credentials
    user = fields.Char(
        string='User', required=True,
    )
    password = fields.Char(
        string='Password', required=True,
    )
    
    # Behavior (FK to AppModel)
    app_model_id = fields.Many2one(
        string='App Model', comodel_name='datacenter.app_model',
    )

    # Configuration
    service_name = fields.Char(
        string='Service Name', required=False,
        default=lambda self: self.name,
    )



class DBModel(models.Model):
    _name = 'datacenter.db_model'
    _description = 'DB Model'
    _inherit = 'datacenter.command_model'
    
    db_ids = fields.One2many(
        string='DBs', comodel_name='datacenter.database',
        inverse_name='db_model_id',
    )


class Database(models.Model):
    _name = 'datacenter.database'
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
    user = fields.Char(
        string='User', required=True,
    )
    password = fields.Char(
        string='Password', required=True,
    )

    # Database model (FK to DBModel)
    db_model_id = fields.Many2one(
        string='DB Model', comodel_name='datacenter.db_model',
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


# Command execution models
# Command is abstract, so it is not created as a table in the database

class Command(models.Model):
    _name = 'datacenter.command'
    _description = 'Command'
    _abstract = True

    name = fields.Char(
        string='Name', required=True,
    )
    description = fields.Text(
        string='Description', required=False,
    )
    command_text = fields.Text(
        string='Command', required=True,
    )
    command_execution_ids = fields.One2many(
        string='Command Executions', comodel_name='datacenter.command_execution',
        inverse_name='command_id',
    )

    # Limit the model to the sames as Server
    command_model = fields.Selection(
        string='Command Model', selection='_get_command_model_selection',
    )

    def _get_object_selection(self):
        return [
            (model.model, model.name) for model in self.env['ir.model'].search([
                ('model', 'in', ['datacenter.server', 'datacenter.application', 'datacenter.database']),
            ])
        ]

    def execute(self, obj, **kwargs):
        if not obj:
            return 'Object not found'
        # Create command execution
        command_text = self.command_text if not kwargs else self.command_text % kwargs
        command_execution = self.env['datacenter.command_execution'].create({
            'command_id': self.id,
            'object_id': obj.id,
            'command_text': self.command_text,
        })
        # Execute command
        command_execution.execute()
        return command_execution


class ServerCommand(models.Model):
    _name = 'datacenter.server_command'
    _description = 'Server Command'
    _inherit = 'datacenter.command'

    def _get_command_model_selection(self):
        return Server._get_server_model_selection(self)

class DatabaseCommand(models.Model):
    _name = 'datacenter.database_command'
    _description = 'Database Command'
    _inherit = 'datacenter.command'

    def _get_command_model_selection(self):
        return Database._get_db_model_selection(self)

class ApplicationCommand(models.Model):
    _name = 'datacenter.application_command'
    _description = 'Application Command'
    _inherit = 'datacenter.command'

    def _get_command_model_selection(self):
        return Application._get_app_model_selection(self)


class CommandExecution(models.Model):
    _name = 'datacenter.command_execution'
    _description = 'Command Execution'
    _transient = True

    command_id = fields.Many2one(
        string='Command', comodel_name='datacenter.command',
    )
    object_id = fields.Reference(
        string='Object', selection='_get_object_selection',
    )
    command_text = fields.Text(
        string='Command', required=True,
    )
    output = fields.Text(
        string='Output', required=False,
    )

    # Get object selection
    def _get_object_selection(self):
        return [
            (model.model, model.name) for model in self.env['ir.model'].search([
                ('model', 'in', ['datacenter.server', 'datacenter.application', 'datacenter.database']),
            ])
        ]

    # Execute command
    def execute(self):
        # No keyword arguments, they are already in the command text
        # Execute command on object. Choose the method depending on the object type
        if self.object_id._name == 'datacenter.server':
            self.output = self.object_id.run_command(self.command_id.name)
        elif self.object_id._name == 'datacenter.application':
            self.output = self.object_id.server_id.run_command(self.command_id.name)
        elif self.object_id._name == 'datacenter.database':
            self.output = self.object_id.run_sql(self.command_id.name)
        else:
            self.output = 'Object type not supported'
        return self.output
