{
    'name': 'Game Profile',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'Store, link, serve and report on game profiles.',
    'sequence': 7,
    'license': 'LGPL-3',
    'author': 'Rafa Guillén',
    'maintainer': 'Rafa Guillén',
    'website': 'https://www.gelectriic.com',
    'depends': ['base', ],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        # XML, CSV, and YML files, etc. that you want to include
        'views/game_profiles_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'datacenter/static/css/game_profile.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
Game Profile
=================

Store game profile data to generate reports and estimates.
Profiles can be linked to a user and a game, as well as provide a list of achievements.
Products and services can be linked to a profile to generate estimates.
Games can use the Odoo API to retrieve profile data.

""",
}
