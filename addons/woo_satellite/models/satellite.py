import base64
import requests
import logging
from odoo import models, fields
from woocommerce import API

_logger = logging.getLogger(__name__)


# Woo Satellite holds the configuration for each WooCommerce store.
# This includes the API keys and the URL of the store.

class WooSatellite(models.Model):
    _name = 'woo_satellite.satellite'
    _description = 'WooCommerce Satellite'
    _rec_name = 'woo_url'

    woo_url = fields.Char(string='Store URL', required=True)
    woo_consumer_key = fields.Char(string='Consumer Key', required=True)
    woo_consumer_secret = fields.Char(string='Consumer Secret', required=True)
    woo_test_ok = fields.Boolean(string='Connect OK?', default=False)

    # Function to get the WooCommerce API object for the current record.
    def get_wcapi(self):
        wcapi = API(
            url=self.woo_url,
            consumer_key=self.woo_consumer_key,
            consumer_secret=self.woo_consumer_secret,
            version="wc/v3"
        )
        return wcapi

    # Add a button to test the connection to the WooCommerce store.
    def test_connection(self):
        for record in self:
            wcapi = record.get_wcapi()
            wcapi.get("products")
            record.write({'woo_test_ok': True})

    # Unset the test_ok flag when the URL, consumer key or consumer secret are changed.
    def write(self, vals):
        if 'woo_url' in vals or 'woo_consumer_key' in vals or 'woo_consumer_secret' in vals:
            vals['woo_test_ok'] = False
        return super(WooSatellite, self).write(vals)

    # Download the products from the WooCommerce store.
    def download_products(self):
        for record in self:
            wcapi = record.get_wcapi()
            products = wcapi.get("products").json()
            for product in products:
                # Create the product in Odoo if it doesn't exist.
                if not record.env['woo_satellite.product'].search([('woo_id', '=', product['id'])]):
                    record.env['woo_satellite.product'].create({
                        'woo_id': product['id'],
                        'woo_satellite_id': record.id,
                        'product_id': record.env['product.product'].create({
                            'name': product['name'],
                            'list_price': product['price'],
                            'standard_price': product['regular_price'],
                        }).id,
                    })
                    if product['images']:
                        response = requests.get(product['images'][0]['src'])
                        if response.status_code != 200:
                            continue
                        response_content = response.content
                        _logger.info("Type of response_content: %s", type(response_content)) #prints the type
                        _logger.info("First 100 characters of response_content: %s", response_content[:100]) #prints the first 100 characters
                        encoded_string = base64.b64encode(response_content).decode()
                        product_id = record.env['woo_satellite.product'].search([('woo_id', '=', product['id'])]).product_id
                        product_id.image_1920 = record.env['ir.attachment'].create({
                            'name': product['images'][0]['name'],
                            'type': 'binary',
                            'datas': encoded_string,
                            'res_model': 'product.product',
                            'res_id': product_id.id,
                        })
                # Update the product in Odoo if it exists.
                else:
                    record.env['woo_satellite.product'].search(
                        [('woo_id', '=', product['id'])]).woo_update_product(product)


# Woo Product holds the information of each product in the WooCommerce store.
# This includes the ID of the product in WooCommerce and the ID of the product in Odoo.

class WooProduct(models.Model):
    _name = 'woo_satellite.product'
    _description = 'WooCommerce Product'
    _rec_name = 'woo_id'

    woo_id = fields.Integer(string='WooCommerce ID', required=True)
    woo_satellite_id = fields.Many2one('woo_satellite.satellite', string='Satellite', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')

    # Function to update the product in Odoo from the WooCommerce data.
    def woo_update_product(self, product):
        for record in self:
            record.product_id.write({
                'name': product['name'],
                'list_price': product['price'],
                'standard_price': product['regular_price'],
            })
