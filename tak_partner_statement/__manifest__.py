# -*- coding: utf-8 -*-
{
    'name': 'Partner Statement',
    'version': '19.1',
    'category': 'Accounting/Accounting',
    'summary': 'Advanced Partner Statement with Multi-Currency Support',
    'description': """
        Partner Statement Report with:
        - Multi-currency support
        - Previous balance and forward balance
        - Summary and Detailed views
        - Invoice line details option
        - Running balance calculation
    """,
    "author": "Takmiil Enterprise Solutions",
    "website": "https://www.takmiil.com/",
    'depends': ['account', 'base'],
    'data': [
        'security/ir.model.access.csv',

        'reports/partner_statement_report.xml',
        'reports/report.xml',

        'wizards/partner_statement_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
