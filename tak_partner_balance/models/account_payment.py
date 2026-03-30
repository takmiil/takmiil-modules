# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Account_payment(models.Model):
    _inherit = "account.payment"

    # partner_balance = fields.Monetary(string="Balance", store=True, compute="_compute_partner_balance")


    # @api.depends('partner_id')
    # def _compute_partner_balance(self):
    #     for record in self:
    #         record.partner_balance = record.partner_id.total_all_due
    