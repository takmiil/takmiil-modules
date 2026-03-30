# -*- coding: utf-8 -*-
{
    'name' : 'Purchase Order Automation',
    'version' : '19.0',
    'category': 'Purchases',
    'maintainer': 'Takmiil Enterprise Solutions',
    'summary': """Enable auto purchase workflow with purchase order confirmation. Include operations like Auto Create bills, Auto Validate bills and Auto Transfer Recipts Order.""",
    'description': """

        You can directly create bills and set done to recipts order by single click

    """,
    'author':'Takmiil Enterprise Solutions',
    'website': 'https://www.takmiil.com/',
    'license': 'LGPL-3',
    'depends' : ['base','purchase', "purchase_stock", "account_payment"],
    'data': [
        'views/stock_warehouse.xml',
        'views/purchase_order.xml'
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/main_screen.png'],

}
