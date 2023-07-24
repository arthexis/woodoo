{
    'name': 'Site Inspection',
    'version': '1.1.8',
    'category': 'Productivity',
    'summary': 'Store on-site inspection data to generate reports and estimates.',
    'sequence': 9,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.arthexis.com',
    'depends': ['base', 'sale_management', ],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/general_inspection_view.xml',
        'views/electrical_inspection_view.xml',
        'views/inspection_menu.xml',
        'security/groups.xml',
        'security/ir.model.access.csv', 
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
Site Inspection
=================
Store on-site inspection data to generate reports and estimates.

This module allows you to define inspection templates and generate reports and estimates from them.

""",
}
