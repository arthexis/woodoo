from odoo import models, fields, api, _

class ServerToolsDashboard(models.Model):
    _name = 'server_tools.dashboard'
    _description = 'Server Tools Dashboard'

    name = fields.Char(
        string='Name',
        required=True,
    )
    server_ids = fields.Many2many(
        comodel_name='server_tools.server',
        string='Servers',
    )


class Server(models.Model):
    _name = 'server_tools.server'
    _description = 'Server'

    name = fields.Char(
        string='Name',
        required=True,
    )
    host = fields.Char(
        string='Host',
        required=True,
    )
    port = fields.Integer(
        string='Port',
        required=True,
    )
    user = fields.Char(
        string='User',
        required=True,
    )
    password = fields.Char(
        string='Password',
        required=True,
    )
    server_action_ids = fields.One2many(
        comodel_name='ir.actions.server',
        inverse_name='server_id',
        string='Server Actions',
    )
    server_tools_dashboard_ids = fields.Many2many(
        comodel_name='server_tools.dashboard',
        string='Dashboards',
    )

    def execute_server_action(self, server_action_id):
        for record in self:
            record.server_action_ids.browse(server_action_id).run()

    def execute_runbook(self, runbook_id):
        for record in self:
            runbook = self.env['server_tools.runbook'].browse(runbook_id)
            for runbook_step in runbook.runbook_step_ids:
                runbook_step.execute()
    