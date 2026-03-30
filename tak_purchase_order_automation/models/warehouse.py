from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    is_receipt_set_to_done = fields.Boolean(string="Is Receipt Set to Done")
    create_bill = fields.Boolean(string="Create Bill?")
    validate_bill = fields.Boolean(string="Validate bill?")