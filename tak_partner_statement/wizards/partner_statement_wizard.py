from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PartnerStatementWizard(models.TransientModel):
    _name = "tak.partner.statement.wizard"
    _description = "Partner Statement Wizard"

    partner_type = fields.Selection(
        [
            ("receivable", "Receivables Only"),
            ("payable", "Payables Only"),
            ("both", "Receivables & Payables"),
        ],
        string="Partner Type",
        required=True,
        default="receivable",
    )

    include_invoice_details = fields.Boolean(
        string="With Invoice Details",
        help="Show product, quantity, unit price and tax details for invoices",
    )

    partner_ids = fields.Many2many(
        "res.partner",
        string="Partners",
        domain=["|", ("customer_rank", ">", 0), ("supplier_rank", ">", 0)],
        help="Leave empty to select all partners (customers and vendors)",
    )

    currency_ids = fields.Many2many(
        "res.currency",
        string="Currencies",
        required=True,
        default=lambda self: self._default_currency_ids(),
        help="Select currencies to include in the statement",
    )

    date_from = fields.Date(
        string="Start Date",
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )

    date_to = fields.Date(string="End Date", default=fields.Date.context_today)

    @api.model
    def _default_currency_ids(self):
        """Get all active currencies by default"""
        return self.env["res.currency"].search([("active", "=", True)])

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("Start Date must be before End Date!"))

    def _prepare_wizard_data(self):
        """Prepare data dict to pass to abstract model"""
        self.ensure_one()
        return {
            "partner_ids": self.partner_ids.ids,
            "currency_ids": self.currency_ids.ids,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "include_invoice_details": self.include_invoice_details,
            "partner_type": self.partner_type,
        }

    def action_print_report(self):
        self.ensure_one()

        data = self._prepare_wizard_data()

        return self.env.ref(
            "tak_partner_statement.action_report_partner_statement"
        ).report_action(self, data=data)
