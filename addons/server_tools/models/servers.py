from odoo import models, fields

class ServerAction(models.Model):
    _name = 'server_tools.action'
    _description = 'Server Action'

    name = fields.Char(
        string='Name',
        required=True,
    )
    server_action_type = fields.Selection(
        selection=[
            ('python', 'Python'),
            ('sql', 'SQL'),
            ('shell', 'Shell'),
        ],
        string='Server Action Type',
        default='python',
        required=True,
    )
    server_action_code = fields.Text(
        string='Server Action Code',
        required=True,
    )
    server_action_runbook_ids = fields.One2many(
        comodel_name='server_tools.runbook',
        inverse_name='server_action_id',
        string='Runbooks',
    )


class Runbook(models.Model):
    _name = 'server_tools.runbook'
    _description = 'Runbook'

    name = fields.Char(
        string='Name',
        required=True,
    )
    server_action_id = fields.Many2one(
        comodel_name='server_tools.action',
        string='Server Action',
        required=True,
    )
    runbook_step_ids = fields.One2many(
        comodel_name='server_tools.runbook_step',
        inverse_name='runbook_id',
        string='Steps',
    )


class RunbookStep(models.Model):
    _name = 'server_tools.runbook_step'
    _description = 'Runbook Step'

    name = fields.Char(
        string='Name',
        required=True,
    )
    runbook_id = fields.Many2one(
        comodel_name='server_tools.runbook',
        string='Runbook',
        required=True,
    )
    server_action_id = fields.Many2one(
        comodel_name='server_tools.action',
        string='Server Action',
        required=True,
    )
    condition = fields.Char(
        string='Condition',
        required=False,
    )
    condition_met = fields.Boolean(
        string='Condition Met',
        compute='_compute_condition_met',
        store=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        required=True,
    )

    def _compute_condition_met(self):
        for record in self:
            record.condition_met = True
            if record.condition:
                try:
                    record.condition_met = eval(record.condition)
                except:
                    record.condition_met = False

    def execute(self):
        for record in self:
            if record.condition_met:
                record.server_action_id.run()
                break
        

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

