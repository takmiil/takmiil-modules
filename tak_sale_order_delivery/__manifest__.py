# -*- coding: utf-8 -*-
{
    "name": "Sale Order Delivery",
    "version": "18.0",
    "category": "Purchases",
    "maintainer": "Takmiil Enterprise Solutions",
    "summary": """This Module Handles Initial Delivery Orders Validations from Sale Order Form""",
    "description": """

       Validate and Create Backorders for Delivey Order from Sale Order Form

    """,
    "author": "Takmiil Enterprise Solutions",
    "website": "https://www.takmiil.com/",
    "license": "LGPL-3",
    "depends": ["base", "sale_stock", "sale"],
    "data": ["views/sales_order.xml"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
