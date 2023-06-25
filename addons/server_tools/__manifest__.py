{
    'name': 'Server Tools',
    'version': '1.0.12',
    'category': 'Tools',
    'summary': 'Tools for managing Odoo servers',
    'sequence': 8,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.gelectriic.com',
    'depends': ['base', ],
    'external_dependencies': {
        'python': ['psutil', 'paramiko', ],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/server_tools_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
Server Tools
=================
This module contains various tools for Odoo server administration.

- Design rich Server Actions to execute Python, SQL or Shell code.
- Monitor Odoo server resources and processes using a dashboard.
- Create runbooks to execute Server Actions and follow conditional logic.
- Manage multiple Odoo servers from a single Odoo instance.

""",
}
