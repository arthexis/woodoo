{
    'name': 'Datacenter',
    'version': '1.0.20',
    'category': 'Tools',
    'summary': 'Tools for managing the Enterprise Datacenter',
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
        'views/datacenter_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
Datacenter
=================
Tools for enterprise datacenter administration.

- Server
- Application
- Process
- Backup
- Restore
- Update
- Upgrade
- Reboot

""",
}
