from odoo import models, fields


# General Inspection Model
# This applies to all types of inspections

class Inspection(models.Model):
    
    _name = 'inspection.record'
    _description = 'General Inspection'

    name = fields.Char(string='Inspection ID', required=True)
    engineer_id = fields.Many2one('res.users', string='Engineer')
    date = fields.Date(string='Inspection Date')
    time = fields.Float(string='Inspection Time')
    location = fields.Char(string='Location')
    customer_comments = fields.Text(string='Customer Comments')
    photo = fields.Binary(string='Photo')
    
    result = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('fail', 'Failure'),
    ], string='Result', default='success')


# Electrical Instaalation Inspection Model
#  This applies to electrical inspections

class ElectricalInstallationInspection(models.Model):
    
    _name = 'electrical.inspection.record'
    _description = 'Electrical Installation Inspection'
    _inherit = 'inspection.record'

    # The two main variables to determine for the installation
    # are Amperage and distance (for sizing the cable)
    # Also the number of turns in the cable should be determined
    # Special requirements for the cable should be determined
    # such as burrowing, wall drilling, etc.

    amperage = fields.Float(string='Amperage')
    distance = fields.Float(string='Distance')
    turns = fields.Integer(string='Turns')
    special_requirements = fields.Text(string='Special Requirements')

# The above model can be visualized with this odoo view:
# <odoo>

# </odoo>
