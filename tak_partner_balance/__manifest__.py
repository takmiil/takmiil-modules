# -*- coding: utf-8 -*-
{
    'name': 'Partner Balance',
    'version': '18.0',
    'summary': """Show Partner Balance in Form, List View and in Payment Form""",
    'author':'Takmiil Enterprise Solutions',
    'website': 'https://www.takmiil.com/',
    'category': 'Accounting',
    'depends': ['base', 'account_payment'],
    "data": [
        "views/res_partner_views.xml"
    ],
    
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
