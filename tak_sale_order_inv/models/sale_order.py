from odoo import _, api, fields, models


from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Total invoiced amount in currency (signed)
    amount_total_in_currency_signed = fields.Monetary(
        string='Total Invoiced',
        currency_field='currency_id',
        compute='_compute_invoice_amounts',
        store=True,
        help="Total amount of all posted invoices"
    )

    # Amount due/residual (signed)
    amount_residual_signed = fields.Monetary(
        string='Amount Due',
        currency_field='currency_id',
        compute='_compute_invoice_amounts',
        store=True,
        help="Remaining amount to be paid from invoices"
    )

    # Optional: Add invoice count for reference
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_amounts',
        store=True
    )

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_total_signed',
                 'invoice_ids.amount_residual_signed', 'invoice_ids.payment_state')
    def _compute_invoice_amounts(self):
        for order in self:
            # Get only posted invoices
            posted_invoices = order.invoice_ids.filtered(
                lambda inv: inv.state == 'posted')

            # Calculate total invoiced amount (signed)
            order.amount_total_in_currency_signed = sum(
                posted_invoices.mapped('amount_total_signed'))

            # Calculate total residual/due amount (signed)
            order.amount_residual_signed = sum(
                posted_invoices.mapped('amount_residual_signed'))

            order.invoice_count = len(posted_invoices)

    # Action to print invoices from sale order
    def action_print_invoices(self):
        """Print all posted invoices for this sale order"""
        self.ensure_one()
        posted_invoices = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted')

        if not posted_invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Invoices',
                    'message': 'There are no posted invoices to print.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # If single invoice, print directly
        if len(posted_invoices) == 1:
            return self.env.ref('account.account_invoices').report_action(posted_invoices)

        # If multiple invoices, print all
        return self.env.ref('account.account_invoices').report_action(posted_invoices)
