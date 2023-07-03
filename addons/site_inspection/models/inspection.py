from odoo import models, fields


# General Inspection Model
# ---------------------------------------
# This applies to all inspections, regardless of type

class Inspection(models.Model):
    
    _name = 'inspection.record'
    _description = 'General Inspection'

    name = fields.Char(string='Inspection ID', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], string='Status', default='draft')

    # Purpose should be a Selection field with these options:
    # 1. Pre-Installation
    # 2. Post-Installation
    # 3. Maintenance
    # 4. Warranty
    # 5. Other
    purpose = fields.Selection([
        ('pre', 'Pre-Installation'),
        ('post', 'Post-Installation'),
        ('maintenance', 'Maintenance'),
        ('warranty', 'Warranty'),
        ('other', 'Other'),
    ], string='Purpose', default='pre')

    engineer_id = fields.Many2one('res.users', string='Engineer')
    date = fields.Date(string='Inspection Date')
    time = fields.Float(string='Inspection Time')
    location = fields.Char(string='Location')

    customer_id = fields.Many2one('res.partner', string='Customer')
    customer_address_id = fields.Many2one('res.partner', string='Customer Address')
    customer_comments = fields.Text(string='Customer Comments')
    
    
    result = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('fail', 'Failure'),
    ], string='Result', default='success')


# Electrical Inspection Model
# ---------------------------------------
# This applies to inspections of electrical systems

# First we setup an AWG table for the cable sizes
# C = Copper, A = Aluminum
# 60 = 60C, 75 = 75C, 90 = 90C
# The values are the Ampacity of the cable
# The values are based on the NEC 2017 Table 310.15(B)(16)

AWG_TABLE = {
    '14': {'C60': 15, 'C75': 20, 'C90': 25, 'A75': 0, 'A90': 0},
    '12': {'C60': 20, 'C75': 25, 'C90': 30, 'A75': 20, 'A90': 25},
    '10': {'C60': 30, 'C75': 35, 'C90': 40, 'A75': 30, 'A90': 35},
    '8': {'C60': 40, 'C75': 50, 'C90': 55, 'A75': 40, 'A90': 45},
    '6': {'C60': 55, 'C75': 65, 'C90': 75, 'A75': 50, 'A90': 55},
    '4': {'C60': 70, 'C75': 85, 'C90': 95, 'A75': 65, 'A90': 75},
    '3': {'C60': 85, 'C75': 100, 'C90': 115, 'A75': 75, 'A90': 85},
    '2': {'C60': 95, 'C75': 115, 'C90': 130, 'A75': 90, 'A90': 100},
    '1': {'C60': 0, 'C75': 130, 'C90': 145, 'A75': 100, 'A90': 115},
    '1/0': {'C60': 0, 'C75': 150, 'C90': 170, 'A75': 120, 'A90': 135},
    '2/0': {'C60': 0, 'C75': 175, 'C90': 195, 'A75': 135, 'A90': 150},
    '3/0': {'C60': 0, 'C75': 200, 'C90': 225, 'A75': 155, 'A90': 175},
    '4/0': {'C60': 0, 'C75': 230, 'C90': 260, 'A75': 180, 'A90': 205},
    '250': {'C60': 0, 'C75': 255, 'C90': 290, 'A75': 205, 'A90': 230},
    '300': {'C60': 0, 'C75': 285, 'C90': 320, 'A75': 230, 'A90': 260},
    '350': {'C60': 0, 'C75': 310, 'C90': 350, 'A75': 250, 'A90': 280},
    '500': {'C60': 0, 'C75': 380, 'C90': 430, 'A75': 310, 'A90': 350},
    '600': {'C60': 0, 'C75': 420, 'C90': 475, 'A75': 340, 'A90': 385},
    '750': {'C60': 0, 'C75': 475, 'C90': 535, 'A75': 385, 'A90': 435},
    '1000': {'C60': 0, 'C75': 545, 'C90': 615, 'A75': 445, 'A90': 500},
}

# Resistivity of copper and aluminum
RESISTIVITY = {'C': 1.68e-8, 'A': 2.82e-8}


class ElectricalInspection(models.Model):
    
    _name = 'electrical.inspection.record'
    _description = 'Electrical Inspection'
    _inherit = 'inspection.record'

    # The two main variables to determine for the installation
    # are Amperage and distance (for sizing the cable)
    # Also the number of turns in the cable should be determined
    # Special requirements for the cable should be determined
    # such as burrowing, wall drilling, etc.

    amperage = fields.Float(string='Amperage')
    distance = fields.Float(
        string='Distance', 
        help='Make sure to consider all turns in the cable'
    )

    # Material of the cable, default is copper
    material = fields.Selection([
        ('C', 'Copper'),
        ('A', 'Aluminum'),
    ], string='Material', default='copper')

    supply_voltage = fields.Selection([
        ('110', '110V'),
        ('220', '220V'),
        ('440', '440V'),
        ('480', '480V'),
    ], string='Supply Voltage')

    # Limit to 60, 75 and 90 with 60 as default
    temperature_rating = fields.Selection([
        ('60', '60C'),
        ('75', '75C'),
        ('90', '90C'),
    ], string='Temperature Rating', default='60')

    turns = fields.Integer(string='Turns')
    cable_size = fields.Selection([
        (key, f'{key} AWG') for key in AWG_TABLE.keys()
    ], string='Cable Size')
    
    # Sizing for the pipes that will contain the cable
    # TODO: Ask Regis what the options are for pipe size and material
    pipe_size = fields.Selection([
        ('1/2', '1/2"'),
        ('3/4', '3/4"'),
        ('1', '1"'),
        ('1 1/4', '1 1/4"'),
        ('1 1/2', '1 1/2"'),
        ('2', '2"'),
        ('2 1/2', '2 1/2"'),
        ('3', '3"'),
        ('3 1/2', '3 1/2"'),
        ('4', '4"'),
        ('5', '5"'),
        ('6', '6"'),
        ('8', '8"'),
        ('10', '10"'),
        ('12', '12"'),
    ], string='Pipe Size')
    pipe_material = fields.Selection([
        ('PVC', 'PVC'),
        ('Steel', 'Steel'),
        ('Aluminum', 'Aluminum'),
    ], string='Pipe Material')

    # Special requirements for the cable
    requires_burrowing = fields.Boolean(string='Requires Burrowing')
    requires_wall_drilling = fields.Boolean(string='Requires Wall Drilling')

    sales_order_id = fields.Many2one('sale.order', string='Sales Order')

    # Determine the cable size based on the amperage and distance.
    # This has to be done in 2 steps. First determine the base cable size
    # based on amperage and temperature rating. Then calculate the AC
    # loss based on the distance, material and supply voltage.
    # Turns do not affect the AC loss for our purposes.
    # If the AC loss would cause the cable not to meet the 3% limit
    # then increase the cable size by 1 and recalculate the AC loss.
    # Repeat until the AC loss is less than 3% or the cable size is 4/0
    # which is the largest size in the table.
    # The 3% limit comes from NEC 2017 210.19(A)(1) FPN No. 4

    def calculate_cable_size(self) -> None:
        base_cable_size = self.get_base_cable_size()
        ac_loss = self.get_ac_loss(base_cable_size)
        while ac_loss > 3 and base_cable_size != '4/0':
            base_cable_size = self.increase_cable_size(base_cable_size)
            ac_loss = self.get_ac_loss(base_cable_size)
        self.cable_size = base_cable_size

    def get_base_cable_size(self) -> str:
        # Get the amperage and temperature rating
        amperage = self.amperage
        temperature_rating = self.temperature_rating
        # Loop through the AWG table and find the cable size
        # that matches the amperage and temperature rating
        for key, value in AWG_TABLE.items():
            if value[f'C{temperature_rating}'] == amperage:
                return key
        # If no match is found then return None
        return None    

    def get_ac_loss(self, base_cable_size: str) -> float:
        resistivity = RESISTIVITY[self.material]
        area = 1 / int(base_cable_size)
        resistance = resistivity * self.distance / area
        voltage_drop = self.amperage * resistance
        power_loss = self.amperage * voltage_drop
        total_power = int(self.supply_voltage) * self.amperage
        ac_loss_percentage = 100 * power_loss / total_power
        return ac_loss_percentage

    def increase_cable_size(self, base_cable_size: str) -> str:
        index = list(AWG_TABLE.keys()).index(base_cable_size)
        next_cable_size = list(AWG_TABLE.keys())[index + 1]
        return next_cable_size

    
    # Tools for generating sales orders and invoices
    def draft_sales_order(self) -> None:
        order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'partner_invoice_id': self.customer_id.id,
            'user_id': self.engineer_id.id,
            'date_order': self.date,
            'state': 'draft',
        })
        self.sales_order_id = order.id
        self.add_cable_to_order(order)


    def add_cable_to_order(self, order: models.Model, color=None) -> None:
        # Consider cable size, material and length
        units = int(self.distance / 3) + 1
        cable = self.env['product.product'].search([
            ('name', '=', 'Cable'),
            ('type', '=', 'product'),
            ('cable_size', '=', self.cable_size),
            ('material', '=', self.material),
            ('color', '=', color or 'black'),
        ], limit=1)
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': cable.id,
            'product_uom_qty': units,
            'product_uom': cable.uom_id.id,
            'price_unit': cable.list_price,
        })


