# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Sale Order Automation",
    "version": "19.1",
    "author": "Takmiil Enterprise Solutions",
    "category": "Sales",
    "maintainer": "Takmiil Enterprise Solutions",
    "summary": """Enable auto sale workflow with sale order confirmation. Include operations like Auto Create Invoice, Auto Validate Invoice and Auto Transfer Delivery Order.""",
    "description": """

        You can directly create invoice and set done to delivery order by single click

    """,
    "website": "https://www.takmiil.com/",
    "license": "LGPL-3",
    "support": "info@takmiil.com",
    "depends": ["sale_stock"],
    "data": [
        "views/stock_warehouse.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "images": ["static/description/main_screen.png"],
}
