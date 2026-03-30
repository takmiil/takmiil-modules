# -*- coding: utf-8 -*-
{
    'name': 'Journal Transfer',
    'version': '19.0',
    'summary': """Transfer Funds Between Journals""",
    'author': 'Takmiil Enterprise Solutions',
    'website': 'https://www.takmiil.com/',
    'category': 'Accounting',
    'depends': ['base', 'mail', 'account'],
    "data": [
        "data/data.xml",
        "security/groups.xml",
        "security/rules.xml",
        "security/ir.model.access.csv",

        "views/journal_transfer_views.xml",
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
