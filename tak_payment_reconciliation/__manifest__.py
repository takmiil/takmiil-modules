# -*- coding: utf-8 -*-
{
    "name": "Payment Reconcillation",
    "summary": """  Reconcile Payment from Payment Form """,
    "description": """
        Reconcile Payment from Payment Form
    """,
    "author": "Takmiil Enterprise Solutions",
    "website": "https://www.takmiil.com/",
    "category": "Accounting",
    "version": "19.1",
    "depends": ["base", "account", 'product'],
    "data": [
        "security/ir.model.access.csv",
        "views/payment.xml",
        "views/product.xml",
        "views/config.xml"
    ],
}
