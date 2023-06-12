from odoo import models, fields


# Woo Satellite holds the configuration for each WooCommerce store.
# This includes the API keys and the URL of the store.

class WooSatellite(models.Model):
    _name = 'woo_satellite.satellite'
    _description = 'WooCommerce Satellite'
    _rec_name = 'woo_url'

    woo_url = fields.Char(string='WooCommerce URL', required=True)
    woo_consumer_key = fields.Char(string='WooCommerce Consumer Key', required=True)
    woo_consumer_secret = fields.Char(string='WooCommerce Consumer Secret', required=True)
    woo_verify_ssl = fields.Boolean(string='Verify SSL', default=True)

