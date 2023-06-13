{
    'name': 'WooSatellite',
    'version': '1.0.14',
    'category': 'Tools',
    'summary': 'Simple WooCommerce integration for Odoo',
    'sequence': 10,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.arthexis.com',
    'depends': ['base', 'sale_management', 'stock', ],
    'external_dependencies': {
        'python': ['woocommerce'],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/woo_satellite_view.xml',
        'views/woo_satellite_menu.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
WooSatellite
=================
Simple WooCommerce integration for Odoo.

Each WooCommerce store is a satellite. This module allows you to connect multiple WooCommerce stores to a single Odoo instance.

* When products are sold on WooCommerce, a Sales Order is created in Odoo. 
* When products are sold or updated in Odoo, the stock is updated in WooCommerce.

Changes in WooCommerce do not affect Odoo and will be overwritten during synchronization, Odoo is the source of truth for the stock.

""",
}
