{
    'name': 'OCPP Station',
    'version': '1.0.30',
    'category': 'Tools',
    'summary': 'Addon for managing OCPP charging stations',
    'sequence': 10,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.gelectriic.com',
    'depends': ['base', 'sale_management', 'stock', ],
    'external_dependencies': {
        'python': ['ocpp'],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/ocpp_server_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
OCPP Station
=================
Addon to manage OCPP charging stations from Odoo.

This addon allows you to define Central Systems and Charging Stations.
It also allows you to define the charging plans for each station.
""",
}
