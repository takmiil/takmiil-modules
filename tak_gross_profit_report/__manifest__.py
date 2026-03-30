{
    "name": "Gross Profit Report",
    "version": "19.1",
    "description": "View Gross Profit Report within a date range by customer, product, and more.",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": ["account"],
    "author": "Takmiil Enterprise Solutions",
    "website": "https://takmiil.com",
    "auto_install": False,
    "application": False,
    "data": [
        "security/ir.model.access.csv",
        "reports/report_gross_profit.xml",
        "reports/report.xml",
        "wizards/gross_profit_wizard_views.xml",
    ],
}