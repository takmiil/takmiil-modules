# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class PartnerStatementAbstract(models.AbstractModel):
    _name = "report.tak_partner_statement.report_tak_partner_statement"
    _description = "Partner Statement"

    def _get_partners(self, partner_ids):
        """Get partners to process (customers and vendors)"""
        domain = ["|", ("customer_rank", ">", 0), ("supplier_rank", ">", 0)]

        if partner_ids:
            domain.append(("id", "in", partner_ids))
            return self.env["res.partner"].search(domain)

        # If no partners selected, get all customers and vendors
        domain.append("|")
        domain.append(("company_id", "=", self.env.company.id))
        domain.append(("company_id", "=", False))
        return self.env["res.partner"].search(domain)

    def _get_previous_balance(self, partner_id, currency_id, date_from, partner_type="both"):
        """Calculate balance before start date based on partner type"""
        if not date_from:
            return 0.0

        domain = [
            ("partner_id", "=", partner_id),
            ("currency_id", "=", currency_id),
            ("date", "<", date_from),
            ("parent_state", "=", "posted"),
        ]
        # Filter by account type based on partner_type
        if partner_type == "receivable":
            domain.append(("account_id.account_type", "=", "asset_receivable"))
        elif partner_type == "payable":
            domain.append(("account_id.account_type", "=", "liability_payable"))
        else:  # both
            domain.append(
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            )

        lines = self.env["account.move.line"].search(domain)

        balance = 0.0
        for line in lines:
            if line.amount_currency:
                balance += line.amount_currency
            else:
                balance += line.debit - line.credit
        return round(balance, 2)

    def _get_move_lines(
        self, partner_id, currency_id, date_from, date_to, partner_type="both"
    ):
        """Get move lines for the period based on partner type"""
        domain = [
            ("partner_id", "=", partner_id),
            ("currency_id", "=", currency_id),
            ("parent_state", "=", "posted"),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))

        if date_to:
            domain.append(("date", "<=", date_to))

        # Filter by account type based on partner_type
        if partner_type == "receivable":
            domain.append(("account_id.account_type", "=", "asset_receivable"))
        elif partner_type == "payable":
            domain.append(("account_id.account_type", "=", "liability_payable"))
        else:  # both
            domain.append(
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            )

        return self.env["account.move.line"].search(domain, order="id asc")

    def _get_invoice_lines(self, move_id):
        """Get detailed invoice lines"""
        invoice = self.env["account.move"].browse(move_id)
        if invoice.move_type not in [
            "out_invoice",
            "out_refund",
            "in_invoice",
            "in_refund",
        ]:
            return []
        return invoice.invoice_line_ids

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Prepare comprehensive statement data
        """
        partner_ids = data.get("partner_ids", [])
        currency_ids = data.get("currency_ids", [])
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        include_invoice_details = data.get("include_invoice_details", False)
        partner_type = data.get("partner_type", "both")

        report_data = []
        grand_totals = {
            "total_debit": 0.0,
            "total_credit": 0.0,
            "final_balance": 0.0,
        }

        # Keep original - no partner_type filter
        partners = self._get_partners(partner_ids)
        currencies = self.env["res.currency"].browse(currency_ids)

        for partner in partners:
            partner_data = {"partner": partner, "currencies": []}

            partner_has_data = False

            for currency in currencies:
                # Pass partner_type to these methods
                prev_balance = self._get_previous_balance(
                    partner.id, currency.id, date_from, partner_type
                )
                move_lines = self._get_move_lines(
                    partner.id, currency.id, date_from, date_to, partner_type
                )

                if not move_lines and prev_balance == 0:
                    continue

                partner_has_data = True
                lines_data = []
                running_balance = prev_balance
                currency_debit = 0.0
                currency_credit = 0.0

                for line in move_lines:
                    if line.amount_currency:
                        debit = (
                            line.amount_currency if line.amount_currency > 0 else 0.0
                        )
                        credit = (
                            abs(line.amount_currency)
                            if line.amount_currency < 0
                            else 0.0
                        )
                    else:
                        debit = line.debit
                        credit = line.credit

                    running_balance += debit - credit
                    currency_debit += debit
                    currency_credit += credit

                    line_data = {
                        "date": line.date,
                        "ref": line.move_name,
                        "name": line.name or "",
                        "debit": debit,
                        "credit": credit,
                        "balance": running_balance,
                        "move_id": line.move_id.id,
                        "type": line.account_id.account_type,
                        "has_invoice_details": include_invoice_details
                        and line.move_id.move_type
                        in ["out_invoice", "out_refund", "in_invoice", "in_refund"],
                    }

                    if include_invoice_details and line_data["has_invoice_details"]:
                        line_data["invoice_lines"] = []
                        for inv_line in self._get_invoice_lines(line.move_id.id):
                            taxes = (
                                ", ".join(inv_line.tax_ids.mapped("name"))
                                if inv_line.tax_ids
                                else ""
                            )
                            line_data["invoice_lines"].append(
                                {
                                    "product": inv_line.product_id.name
                                    or inv_line.name,
                                    "quantity": inv_line.quantity,
                                    "unit_price": inv_line.price_unit,
                                    "tax": taxes,
                                    "subtotal": inv_line.price_subtotal,
                                }
                            )

                    lines_data.append(line_data)

                forward_balance = running_balance

                grand_totals["total_debit"] += currency_debit
                grand_totals["total_credit"] += currency_credit

                currency_data = {
                    "currency": currency,
                    "previous_balance": prev_balance,
                    "forward_balance": forward_balance,
                    "lines": lines_data,
                    "show_currency_header": len(currencies) > 1,
                    "currency_totals": {
                        "debit": currency_debit,
                        "credit": currency_credit,
                    },
                }

                partner_data["currencies"].append(currency_data)

            if partner_has_data:
                report_data.append(partner_data)

        grand_totals["final_balance"] = sum(
            curr["forward_balance"]
            for partner in report_data
            for curr in partner["currencies"]
        )

        return {
            "data": report_data,
            "grand_totals": grand_totals,
            "show_multiple_currencies": len(currencies) > 1,
            "show_multiple_partners": len(partners) > 1,
            "date_from": date_from,
            "date_to": date_to,
            "include_invoice_details": include_invoice_details,
            "partner_type": partner_type,  # Add to return data
        }
