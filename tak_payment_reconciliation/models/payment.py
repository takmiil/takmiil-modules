# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    invoice_selection_ids = fields.One2many(
        "account.payment.invoice.line",
        "payment_id",
        string="Select Invoices",
    )
    customer_discount_product_id = fields.Many2one(
        string="Discount Item",
        comodel_name="product.template",
    )

    vendor_discount_product_id = fields.Many2one(
        string="Discount Item",
        comodel_name="product.template",
    )
    write_off_amount = fields.Monetary(string="Discount Amount", store=True)
    has_discount = fields.Boolean(string="Discount")

    # NEW FIELD: Track the separate discount journal entry
    discount_move_id = fields.Many2one(
        "account.move",
        string="Discount Journal Entry",
        readonly=True,
        copy=False,
        help="Separate journal entry created for the discount amount",
    )

    def _get_invoices(self):
        for rec in self:
            rec.invoice_selection_ids = [(5, 0, 0)]

            if not rec.partner_id or rec.state != "draft":
                continue

            domain = [
                ("partner_id", "child_of", rec.partner_id.id),
                ("state", "=", "posted"),
                ("payment_state", "in", ["not_paid", "partial"]),
            ]

            if rec.partner_type == "customer":
                domain.append(("move_type", "=", "out_invoice"))
            elif rec.partner_type == "supplier":
                domain.append(("move_type", "=", "in_invoice"))
            else:
                continue

            invoices = self.env["account.move"].search(domain, order="invoice_date asc")
            lines = [(0, 0, {"invoice_id": inv.id}) for inv in invoices]
            rec.invoice_selection_ids = lines

    @api.onchange("partner_id", "partner_type")
    def _onchange_partner_invoice_selection(self):
        self._get_invoices()

    
    @api.onchange("amount", "partner_id", "partner_type")
    def _onchange_amount_auto_select(self):
        if not self.invoice_selection_ids or self.amount <= 0:
            return

        already_selected = self.invoice_selection_ids.filtered("selected")
        if already_selected:
            return

        sorted_lines = self.invoice_selection_ids.sorted(key=lambda x: x.invoice_date or fields.Date.today())

        remaining = self.amount
        for line in sorted_lines:
            if remaining <= 0:
                break
            # Used absolute value since vendor bills have negative amount_due
            due_amount = abs(line.amount_due)
            if due_amount > 0:
                line.selected = True
                remaining -= due_amount


    @api.onchange("has_discount")
    def _onchange_has_discount_auto_fill(self):
        if not self.has_discount:
            return

        selected_lines = self.invoice_selection_ids.filtered("selected")
        if not selected_lines:
            return

        # Used absolute values since vendor bills have negative amount_due
        total_due = sum(abs(line.amount_due) for line in selected_lines)
        total_applied = sum(line.amount_applied for line in selected_lines)

        residual = total_due - total_applied

        if residual > 0 and (not self.write_off_amount or self.write_off_amount == 0):
            self.write_off_amount = residual


    def action_post(self):
        self._validate_payments()
        for payment in self:
            super(AccountPayment, payment).action_post()
            if payment.has_discount:
                self._handle_discount_accounting(payment)
            if payment.invoice_selection_ids:
                self._reconcile_selected_invoices(payment)
        return True

    def _validate_payments(self):
        for payment in self:
            if not payment.has_discount:
                continue

            if payment.partner_type == "customer" and not payment.customer_discount_product_id:
                raise UserError(_("Please select the Customer Discount Item!"))

            if  payment.partner_type == "supplier" and not payment.vendor_discount_product_id:
                raise UserError("Please select the Vendor Discount Item!")

            if payment.write_off_amount <= 0:
                raise UserError("Discount amount must be greater than zero if 'Discount' is checked.")


    def _handle_discount_accounting(self, payment):
        if payment.partner_type == "customer":
            product = payment.customer_discount_product_id
            discount_account = product.property_account_expense_id or product.categ_id.property_account_expense_categ_id
        else:
            product = payment.vendor_discount_product_id
            discount_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id

        if not discount_account:
            raise UserError("The product '%s' has no account defined.") % product.name
            
        default_journal_id = self.env.company.discount_journal_id.id

        if not default_journal_id: 
            raise UserError("Please configure the Default Discount Journal in Settings!")

        move_lines = []
        total_discount = payment.write_off_amount

        if payment.partner_type == "customer":
            receivable_account = payment.destination_account_id

            move_lines.append(
                (0,0,{
                        "account_id": discount_account.id,
                        "partner_id": payment.partner_id.id,
                        "name": _("Discount: %s") % payment.partner_id.name,
                        "debit": total_discount,
                        "credit": 0.0,
                    },
                )
            )
            move_lines.append(
                (0,0,{
                        "account_id": receivable_account.id,
                        "partner_id": payment.partner_id.id,
                        "name": _("Discount Write-off: %s") % payment.name,
                        "debit": 0.0,
                        "credit": total_discount,
                    },
                )
            )
        else:
            payable_account = payment.destination_account_id

            move_lines.append(
                (0,0,{
                        "account_id": payable_account.id,
                        "partner_id": payment.partner_id.id,
                        "name": _("Discount Write-off: %s") % payment.name,
                        "debit": total_discount,
                        "credit": 0.0,
                    },
                )
            )
            move_lines.append(
                (0,0,{
                        "account_id": discount_account.id,
                        "partner_id": payment.partner_id.id,
                        "name": _("Discount: %s") % payment.partner_id.name,
                        "debit": 0.0,
                        "credit": total_discount,
                    },
                )
            )

        discount_move = self.env["account.move"].create(
            {
                "journal_id": default_journal_id,
                "date": payment.date,
                "ref": _("Discount for Payment: %s") % payment.name,
                "line_ids": move_lines,
            })

        discount_move.action_post()

        
        payment.discount_move_id = discount_move.id

        self._reconcile_discount_move(payment, discount_move)

    def _reconcile_discount_move(self, payment, discount_move):
        try:
            # Find the receivable/payable line in payment move
            payment_line = payment.move_id.line_ids.filtered(lambda l: l.account_id == payment.destination_account_id and not l.reconciled)

            # Find the opposite line in discount move (same account)
            discount_line = discount_move.line_ids.filtered(lambda l: l.account_id == payment.destination_account_id and not l.reconciled)

            if payment_line and discount_line:
                (payment_line + discount_line).reconcile()
        except Exception as e:
            _logger.warning("Could not reconcile discount move automatically: %s", str(e))

    def _reconcile_selected_invoices(self, payment):
        if not payment.invoice_selection_ids:
            return

        selected_lines = payment.invoice_selection_ids.filtered(lambda l: l.selected and l.invoice_id.state == "posted")

        reconciliation_errors = []

        for line in selected_lines:
            try:
                invoice = line.invoice_id

                target_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type in ["asset_receivable", "liability_payable"]and not l.reconciled)

                if not target_lines:
                    reconciliation_errors.append(f"Invoice {invoice.name}: No unreconciled payable/receivable lines found")
                    continue

                
                payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == target_lines[0].account_id and not l.reconciled)

                if not payment_lines:
                    reconciliation_errors.append(f"Invoice {invoice.name}: No matching payment lines found")
                    continue

                
                lines_to_reconcile = target_lines + payment_lines
                lines_to_reconcile.reconcile()

                invoice.payment_reference = payment.name

            except Exception as e:
                reconciliation_errors.append(f"Invoice {invoice.name}: {str(e)}")

        
        if reconciliation_errors:
            error_message = "Reconciliation errors:\n" + "\n".join(reconciliation_errors)
            _logger.warning(f"Payment {payment.name} reconciliation issues: {error_message}")
            payment.message_post(body=f"Reconciliation warnings: {error_message}")

    def select_all(self):
        if self.invoice_selection_ids and self.state == "draft":
            self.invoice_selection_ids.write({"selected": True})

    def deselect_all(self):
        if self.invoice_selection_ids and self.state == "draft":
            self.invoice_selection_ids.write({"selected": False})

    def action_draft(self):
        res = super().action_draft()

        for payment in self:
            if payment.discount_move_id:
                if payment.discount_move_id.state == "posted":
                    payment.discount_move_id.button_cancel()
                    
            self._get_invoices()

        return res

    def action_open_discount_journal_entry(self):

        return {
            "name": _("Discount Journal"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "account.move",
            "context": {"create": False},
            "views": [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
            "domain": [("id", "in", self.discount_move_id.ids)],
        }
