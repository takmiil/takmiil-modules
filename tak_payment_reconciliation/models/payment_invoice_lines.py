# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging


class AccountPaymentInvoiceLine(models.Model):
    _name = "account.payment.invoice.line"
    _description = "Selectable Invoice for Payment"

    payment_id = fields.Many2one("account.payment", ondelete='cascade')
    invoice_id = fields.Many2one("account.move", string="Invoice or Bill")
    selected = fields.Boolean()
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    invoice_date = fields.Date(related="invoice_id.invoice_date", string="Invoice Date")
    amount_total = fields.Monetary(
        related="invoice_id.amount_total_signed", string="Total Amount"
    )
    state = fields.Selection(related="invoice_id.payment_state", string="Status")
    amount_due = fields.Monetary(related="invoice_id.amount_residual_signed")
    amount_applied = fields.Monetary(
        string="Amount Applied", compute="_compute_amount_applied", store=True
    )
    residual  = fields.Monetary(
    string="Residual",
    compute="_compute_residual",
    store=True
    )
    selection_disabled = fields.Boolean(
        string="Disable Selection", compute="_compute_selection_disabled", store=False
    )
    selection_sequence = fields.Integer(string="Selection Order", default=0)
    
    

    @api.onchange("selected")
    def _onchange_selected(self):
        for line in self:
            if line.selected and not line.selection_sequence:
                max_seq = max(
                    line.payment_id.invoice_selection_ids.mapped("selection_sequence")
                    or [0]
                )
                line.selection_sequence = max_seq + 1
            elif not line.selected:
                line.selection_sequence = 0

    @api.depends(
        "selected",
        "selection_sequence",
        "payment_id.amount",
        "payment_id.has_discount",
        "payment_id.write_off_amount",
    )
    def _compute_amount_applied(self):
        for payment in self.mapped("payment_id"):
            total_to_allocate = payment.amount
            if payment.has_discount:
                total_to_allocate += payment.write_off_amount or 0.0

            remaining = total_to_allocate

            selected_lines = payment.invoice_selection_ids.filtered("selected").sorted(
                key=lambda x: x.selection_sequence
            )

            for line in selected_lines:
                residual = abs(line.invoice_id.amount_residual_signed)
                applied_to_l = min(residual, remaining) if remaining > 0 else 0.0
                line.amount_applied = applied_to_l
                remaining -= applied_to_l

            for line in payment.invoice_selection_ids - selected_lines:
                line.amount_applied = 0.0

    @api.depends("amount_due", "amount_applied")
    def _compute_residual(self):
        for line in self:
            # Handle both positive (customer) and negative (vendor) amounts
            line.residual = abs(line.amount_due) - line.amount_applied


    @api.depends(
        "selected",
        "payment_id.amount",
        "payment_id.write_off_amount",
        "payment_id.invoice_selection_ids.amount_applied",
    )
    def _compute_selection_disabled(self):
        for line in self:
            payment = line.payment_id
            total_to_allocate = payment.amount + (payment.write_off_amount or 0.0)

            if total_to_allocate <= 0:
                line.selection_disabled = False
                continue

            total_allocated = sum(
                l.amount_applied for l in payment.invoice_selection_ids
            )

            if line.selected:
                line.selection_disabled = False
            else:
                remaining = total_to_allocate - total_allocated
                line.selection_disabled = remaining <= 0
