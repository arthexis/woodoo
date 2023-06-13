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
                record.env['woo_satellite.product'].woo_update_product(product)


# Woo Product holds the information of each product in the WooCommerce store.
# This includes the ID of the product in WooCommerce and the ID of the product in Odoo.

class WooProduct(models.Model):
    _name = 'woo_satellite.product'
    _description = 'WooCommerce Product'
    _rec_name = 'woo_id'

    woo_id = fields.Integer(string='WooCommerce ID', required=True)
    woo_satellite_id = fields.Many2one('woo_satellite.satellite', string='Satellite', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)

    # Function to update the product in Odoo from the WooCommerce data.
    def woo_update_product(self, product):
        for record in self:
            record.product_id.write({
                'name': product['name'],
                'list_price': product['price'],
                'standard_price': product['regular_price'],
            })
