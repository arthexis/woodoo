{
    'name': 'Power Tome',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'Create and manage Evennia games.',
    'sequence': 7,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.gelectriic.com',
    'depends': ['base', 'datacenter'],
    'external_dependencies': {
        'python': ['evennia', ],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/power_tome_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'datacenter/static/css/power_tome.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
Power Tome
=================

Create and manage Evennia games.

Evennia is a Python MUD server, a program that allows you to create and run your own 
multiplayer text-based worlds. Evennia is a modern library for creating online
 multiplayer text games (MUD, MUSH, MUX, MUCK, MOO etc) in pure Python. 
 It allows game creators to design and flesh out their ideas with great freedom. 
 Evennia is made available under the open-source BSD license.

This module allows you to create and manage Evennia games from Odoo.

""",
}
