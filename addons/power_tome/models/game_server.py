# Game Server models

import evennia
from odoo import models, fields, api, _


class GameServer(models.Model):
    _name = 'power_tome.game.server'
    _description = 'Game Server'

    _inherit = 'datacenter.app.server'

    # Game server status
    game_status = fields.Selection(
        string='Game Status', required=True,
        selection=[
            ('stopped', 'Stopped'),
            ('running', 'Running'),
            ('starting', 'Starting'),
            ('stopping', 'Stopping'),
        ],
        default='stopped',
    )
    game_pid = fields.Integer(
        string='Game PID', required=False,
    )
