{
    "name": "Journal Statement",
    "version": "19.1",
    "description": "View Journal Statement within a date range",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": ["account"],
    "author": "Takmiil Enterprise Solutions",
    "website": "https://takmiil.com",
    "auto_install": False,
    "application": False,
    "data": [
        "security/ir.model.access.csv",
        "reports/journal_statement_report.xml",
        "reports/report.xml",
        "wizards/journal_statement_wizard.xml",
    ],
}
