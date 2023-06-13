from odoo import models, fields
from woocommerce import API


# Woo Satellite holds the configuration for each WooCommerce store.
# This includes the API keys and the URL of the store.

class WooSatellite(models.Model):
    _name = 'woo_satellite.satellite'
    _description = 'WooCommerce Satellite'
    _rec_name = 'woo_url'

    woo_url = fields.Char(string='Store URL', required=True)
    woo_consumer_key = fields.Char(string='Consumer Key', required=True)
    woo_consumer_secret = fields.Char(string='Consumer Secret', required=True)
    woo_test_ok = fields.Boolean(string='Test OK?', default=False)

    # Add a button to test the connection to the WooCommerce store.
    def test_connection(self):
        for record in self:
            wcapi = API(
                url=record.woo_url,
                consumer_key=record.woo_consumer_key,
                consumer_secret=record.woo_consumer_secret,
                version="wc/v3"
            )
            wcapi.get("products")
            record.write({'woo_test_ok': True})

