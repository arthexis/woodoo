import logging
import math
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)

# Notes:

# _calculate functions should change fields in the model in-place
# _validate functions should raise an exception if the validation fails
# _get functions should return a value

# General Inspection Model
# This applies to all inspections, regardless of type

class Inspection(models.Model):
    
    _name = 'inspection.record'
    _description = 'General Inspection'

    # Purpose of the inspection
    purpose = fields.Selection([
        ('pre', 'Pre-Installation'),
        ('post', 'Post-Installation'),
        ('maintenance', 'Maintenance'),
        ('warranty', 'Warranty'),
        ('other', 'Other'),
    ], string='Purpose', default='pre')

    # Status of the inspection
    # Allow the engineer to set the status manually or automatically
    status = fields.Selection([
        ('pending', 'Pending'), 
        ('validated', 'Validated'),
        ('calculated', 'Calculated'),
        ('failure', 'Failed'),
        ('drafted', 'Quote Drafted'),
        ('archived', 'Archived'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending')

    engineer_id = fields.Many2one(
        'res.users', string='Engineer', default=lambda self: self.env.user)
    date = fields.Date(string='Inspection Date', default=fields.Date.today)
    customer_id = fields.Many2one('res.partner', string='Customer')
    location = fields.Char(string='Location', help='Describe the location')

    customer_notes = fields.Text(string='Customer Notes')
    engineer_notes = fields.Text(string='Engineer Notes')

    # Name for the inspection = customer name + short date
    def name_get(self):
        result = []
        for record in self:
            name = f'{record.customer_id.name} - {record.date}'
            result.append((record.id, name))
        return result


# Electrical Inspection Model
# This applies to inspections of electrical systems

# First we setup an AWG table for the cable sizes
# C = Copper, A = Aluminum
# 60 = 60C, 75 = 75C, 90 = 90C
# The values are the Ampacity of the cable
# The values are based on the NEC 2017 Table 310.15(B)(16)

AWG_TEMP_AMPACITY = {
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
}


# Resistivity of copper and aluminum
RESISTIVITY = {'C': 1.68e-8, 'A': 2.82e-8}


AWG_DIAMETER_INCHES = {
    '4/0': 0.46,
    '3/0': 0.4096,
    '2/0': 0.3648,
    '1/0': 0.3249,
    '1': 0.2893,
    '2': 0.2576,
    '3': 0.2294,
    '4': 0.2043,
    '6': 0.162,
    '8': 0.1285,
    '10': 0.1019,
}

CONDUIT_SIZES_INCHES = {
    '1/2': 0.5,
    '3/4': 0.75,
    '1': 1.0,
    '1 1/4': 1.25,
    '1 1/2': 1.5,
    '2': 2.0,
    '2 1/2': 2.5,
}


class ElectricalInspection(models.Model):
    
    _name = 'electrical.inspection.record'
    _description = 'Electrical Inspection'
    _inherit = 'inspection.record'

    # The two main variables to determine for the installation
    # are Amperage and distance (for sizing the cable)
    # Also the number of turns in the cable should be determined
    # Special requirements for the cable should be determined
    # such as burrowing, wall drilling, etc.

    amperage = fields.Integer(string='Amperage', default=32)
    distance = fields.Integer(
        string='Distance', 
        unit='meters',
        help='Make sure to consider all turns in the cable'
    )

    num_chargers = fields.Integer(string='Number of Chargers', default=1)
    num_cables = fields.Integer(string='Number of Cables', default=1)

    # Material of the cable, default is copper
    cable_material = fields.Selection([
        ('C', 'Copper'),
        ('A', 'Aluminum'),
    ], string='Cable Material', default='C')

    supply_voltage = fields.Selection([
        ('110', '110V'),
        ('220', '220V'),
        ('440', '440V'),
        ('480', '480V'),
    ], string='Supply Voltage', default='220')

    # Limit to 60, 75 and 90 with 60 as default
    temperature_rating = fields.Selection([
        ('60', '60C'),
        ('75', '75C'),
        ('90', '90C'),
    ], string='Temp. Rating', default='60')

    turns = fields.Integer(string='Turns')
    cable_size = fields.Selection([
        (key, f'{key} AWG') for key in AWG_TEMP_AMPACITY.keys()
    ], string='Cable Size')
    
    # Sizing for the pipes that will contain the cable
    pipe_size = fields.Selection([
        (key, f'{key}"') for key in CONDUIT_SIZES_INCHES.keys()
    ], string='Pipe Size')

    pipe_material = fields.Selection([
        ('PVC', 'PVC'),
        ('Steel', 'Steel'),
        ('Aluminum', 'Aluminum'),
    ], string='Pipe Material', default='PVC')

    # Special requirements for the cable
    req_burrowing = fields.Boolean(string='Requires Burrowing')
    req_wall_drilling = fields.Boolean(string='Requires Wall Drilling')

    sales_order_id = fields.Many2one('sale.order', string='Sales Order')

    def checks(self) -> None:
        error_msg = None
        try:
            self._validate_observations()
            self.status = 'validated'
        except Exception as error:
            error_msg = error.args[0]
            self.status = 'pending'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Checks Passed' if not error_msg else 'Checks Failed',
                'message': 'Proceed to calculations.' if not error_msg else error_msg,
                'type': 'success' if not error_msg else 'danger',
                'sticky': False,
            }
        }

    def calculate(self) -> None:
        try:
            self._calculate_cable()
            self._calculate_pipe()
            self._validate_calculation()
            self.status = 'calculated'
        except Exception as error:
            self.status = 'validated'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Calculate Failed',
                    'message': error.args[0],
                    'type': 'danger',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def quote(self) -> None:
        try:
            self._draft_sales_order()
            self.status = 'drafted'
        except Exception as error:
            self.status = 'calculated'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Estimate failed',
                    'message': error.args[0],
                    'type': 'danger',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _validate_observations(self) -> None:
        assert self.amperage > 1, 'Amperage is 1 or less'
        assert self.num_chargers > 0, 'Number of chargers is 0'
        assert self.num_cables in (1, 3), 'Number of cables is not 1 or 3'
        assert self.distance > 2, 'Distance is less than 3 meters'
        assert self.cable_material, 'Cable material not defined'
        assert self.supply_voltage, 'Supply voltage not defined'
        assert self.temperature_rating, 'Temperature rating not defined'
        assert self.turns > 0, 'Number of turns not counted'
        # TODO: Check for additional required validations
        _logger.info('Observations validated')

    def _validate_calculation(self) -> None:
        assert self.cable_size, 'Cable size not calculated'
        assert self.pipe_size, 'Pipe size not calculated'
        assert self.pipe_material, 'Pipe material not calculated'
        # TODO: Check for additional required validations
        _logger.info('Calculation validated')

    # First we calculate the cable size based on the amperage and distance
    # Then we increase the cable size until the AC loss is less than 3%
    # This is required by NEC 2017
    def _calculate_cable(self) -> None:
        cable_size = self._get_base_cable_size()
        ac_loss = self._get_ac_loss(cable_size)
        while ac_loss > 3 and cable_size != '4/0':
            cable_size = self._get_next_cable_size(cable_size)
            ac_loss = self._get_ac_loss(cable_size)
        self.cable_size = cable_size
        _logger.info(f'Final cable size: {cable_size}')  
        
    def _get_base_cable_size(self) -> str:
        amperage = int(self.amperage)
        temp_rating = self.temperature_rating
        for cable_size, temp_to_amps in AWG_TEMP_AMPACITY.items():
            if temp_to_amps[f'C{temp_rating}'] >= amperage:
                _logger.info(f'Base cable size: {cable_size}')
                return cable_size
        raise exceptions.UserError('No cable size defined for amperage and temperature')

    # Calculate the AC loss for the cable based on the amperage and distance
    def _get_ac_loss(self, base_cable_size: str) -> float:
        resistivity = RESISTIVITY[self.cable_material]
        conduit_area = self._get_awg_area(base_cable_size)
        resistance = resistivity * self.distance / conduit_area
        voltage_drop = self.amperage * resistance
        power_loss = self.amperage * voltage_drop
        total_power = int(self.supply_voltage) * self.amperage
        ac_loss_percentage = 100 * power_loss / total_power
        _logger.info(f'AC loss: {ac_loss_percentage}')
        return ac_loss_percentage

    # Calculate the circular area for an AWG cable based on its diameter
    def _get_awg_area(self, diameter: str) -> float:
        d = AWG_DIAMETER_INCHES.get(diameter)
        if d is None:
            raise ValueError(f"Invalid AWG size: {diameter}")
        # Calculate the area using the formula for area of a circle
        return math.pi * (d / 2)**2

    def _get_next_cable_size(self, base_cable_size: str) -> str:
        index = list(AWG_TEMP_AMPACITY.keys()).index(base_cable_size)
        next_cable_size = list(AWG_TEMP_AMPACITY.keys())[index + 1]
        return next_cable_size

    def _draft_sales_order(self) -> None:
        order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'partner_invoice_id': self.customer_id.id,
            'user_id': self.engineer_id.id,
            'date_order': self.date,
            'state': 'draft',
        })
        self.sales_order_id = order.id
        self._add_cable_to_order(order)

    def _add_cable_to_order(self, order: models.Model, color=None) -> None:
        units = self._get_cable_units()
        if not (cable := self.env['product.product'].search([
            ('name', '=', 'Cable'),
            ('type', '=', 'product'),
            ('material', '=', self.cable_material),
            ('color', '=', color or 'black'),
        ], limit=1)):
            raise exceptions.UserError('Cable not found in product list')
        else:
            _logger.info(f'Adding {units} units of {cable.name} to order')
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': cable.id,
                'product_uom_qty': units,
                'product_uom': cable.uom_id.id,
                'price_unit': cable.list_price,
            })
            _logger.info(f'Added {units} units of {cable.name} to order')

    def _get_cable_units(self) -> int:
        return math.ceil(self.distance / 3) * self.num_chargers * self.num_cables

    # TODO: Implement the _calculate_required_pipe_size and _find_smallest_suitable_conduit methods

    def _calculate_pipe(self) -> None:
        # First use the AWG diameter to calculate the area of the cable
        # The NEC specifications are: One wire: maximum fill is 53% of the space inside a conduit. 
        # Two wires: maximum fill is 31% 
        # Three wires or more: maximum fill is 40% of the conduit's total available space.
        cable_area = self._get_awg_area(self.cable_size)
        if self.num_cables == 1:
            max_fill = 0.53
        elif self.num_cables == 2:
            max_fill = 0.31
        else:
            max_fill = 0.4
        # Then calculate the required pipe area
        required_pipe_area = cable_area * self.num_cables / max_fill
        # Then calculate the required pipe diameter
        required_pipe_diameter = math.sqrt(required_pipe_area / math.pi) * 2
        # Then find the smallest suitable conduit using the table (inline)
        self.pipe_size = self._get_smallest_suitable_conduit(required_pipe_diameter)
        _logger.info(f'Final pipe size: {self.pipe_size}')

    def _get_smallest_suitable_conduit(self, required_pipe_diameter: float) -> str:
        # Use the pipe sizes, picking the smallest one that is larger than the required diameter
        # From CONDUIT_SIZES_INCHES
        for pipe_size, pipe_diameter in CONDUIT_SIZES_INCHES:
            if pipe_diameter >= required_pipe_diameter:
                return pipe_size
        raise exceptions.UserError('No suitable pipe size found')
