{
    'name': 'Datacenter',
    'version': '1.4.9',
    'category': 'Tools',
    'summary': 'Tools for managing the Enterprise Datacenter',
    'sequence': 8,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.arthexis.com',
    'depends': ['base', ],
    'external_dependencies': {
        'python': ['psutil', 'paramiko', 'psycopg2'],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/datacenter_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'datacenter/static/css/datacenter.css',
            #'datacenter/static/src/js/datacenter.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
Datacenter
=================
Tools for enterprise datacenter administration.

- Includes models for:
    - Server management
    - Application management
    - Database management
    - Domain management

""",
}
