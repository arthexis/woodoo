from odoo import models, fields
from base64 import b64decode
from io import StringIO
from paramiko import SSHClient, AutoAddPolicy, RSAKey


# Datacenter models

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
    user = fields.Char(
        string='User', required=False,
    )
    password = fields.Char(
        string='Password', required=False,
    )
    # Store PEM key as file upload
    private_pem_file = fields.Binary(
        string='Private PEM File', attachment=True)
    private_pem_file_name = fields.Char(
        string='Private PEM File Name'
    )
    application_ids = fields.One2many(
        string='Applications', comodel_name='datacenter.application',
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
    errors = fields.Text(
        string='Errors', required=False,
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
    def run_command(self, command=None):
        if not command:
            command = self.command
        ssh = self.get_ssh()
        stdin, stdout, stderr = ssh.exec_command(command)
        # Store command output
        self.output = stdout.read().decode()
        self.errors = stderr.read().decode()
        return self.output


class Application(models.Model):
    _name = 'datacenter.application'
    _description = 'Application'

    name = fields.Char(
        string='Name', required=True,
    )
    server_id = fields.Many2one(
        string='Server', comodel_name='datacenter.server',
    )
    user = fields.Char(
        string='User', required=True,
    )
    password = fields.Char(
        string='Password', required=True,
    )
    app_port = fields.Integer(
        string='App Port', required=False, default=80,
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


# Command execution models

class Command(models.Model):
    _name = 'datacenter.command'
    _description = 'Command'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name', required=True,
    )
    description = fields.Text(
        string='Description', required=False,
    )
    command_execution_ids = fields.One2many(
        string='Command Executions', comodel_name='datacenter.command_execution',
        inverse_name='command_id',
    )

    # Execute command on a single object
    def execute_on_object(self, obj):
        # Create command execution
        command_execution = self.env['datacenter.command_execution'].create({
            'command_id': self.id,
            'object_id': obj.id,
        })
        # Execute command
        command_execution.execute()
        return command_execution

    # Execute command on a list of objects
    def execute_on_objects(self, objects):
        # Create command executions
        command_executions = self.env['datacenter.command_execution'].create([{
            'command_id': self.id,
            'object_id': obj.id,
        } for obj in objects])
        # Execute commands
        for command_execution in command_executions:
            command_execution.execute()
        return command_executions


class ServerCommand(models.Model):
    _name = 'datacenter.server_command'
    _description = 'Server Command'
    _inherit = 'datacenter.command'

    # Execute command on a single server with SSH
    def execute_on_server(self, server):
        return self.execute_on_object(server)

    # Execute command on a list of servers
    def execute_on_servers(self, servers):
        return self.execute_on_objects(servers)


class DatabaseCommand(models.Model):
    _name = 'datacenter.database_command'
    _description = 'Database Command'
    _inherit = 'datacenter.command'

    # Execute command on a single database
    def execute_on_database(self, database):
        return self.execute_on_object(database)

    # Execute command on a list of databases
    def execute_on_databases(self, databases):
        return self.execute_on_objects(databases)
    

class ApplicationCommand(models.Model):
    _name = 'datacenter.application_command'
    _description = 'Application Command'
    _inherit = 'datacenter.command'

    # Execute command on a single application
    def execute_on_application(self, application):
        return self.execute_on_object(application)

    # Execute command on a list of applications
    def execute_on_applications(self, applications):
        return self.execute_on_objects(applications)


class CommandExecution(models.Model):
    _name = 'datacenter.command_execution'
    _description = 'Command Execution'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    command_id = fields.Many2one(
        string='Command', comodel_name='datacenter.command',
    )
    object_id = fields.Reference(
        string='Object', selection='_get_object_selection',
    )
    output = fields.Text(
        string='Output', required=False,
    )
    errors = fields.Text(
        string='Errors', required=False,
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
        # Execute command on object. Choose the method depending on the object type
        if self.object_id._name == 'datacenter.server':
            # run_command() method is defined in the Server model
            self.output = self.object_id.run_command(self.command_id.name)
        elif self.object_id._name == 'datacenter.application':
            # run_command() method is defined in the Server model
            self.output = self.object_id.server_id.run_command(self.command_id.name)
        elif self.object_id._name == 'datacenter.database':
            # run_sql() method is defined in the Database model
            self.output = self.object_id.run_sql(self.command_id.name)
        else:
            self.output = 'Object type not supported'
        return self.output
