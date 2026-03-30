
# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    tak_transfer_id = fields.Many2one(
        'tak.journal.transfer',
        string='TAK Transfer',
        readonly=True,
        copy=False,
        index=True,
        ondelete='cascade'
    )
