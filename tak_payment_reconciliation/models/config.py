# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError



class ResCompany(models.Model):
    _inherit = "res.company"
    
    
    discount_journal_id = fields.Many2one(
        'account.journal',
        string='Default Discount Journal',
        domain=[('type','=', 'general')],
        help='Journal used for discount entries when processing payments with write-offs'
    )



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    discount_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.discount_journal_id',
        string='Default Discount Journal',
        readonly=False,
        help='Journal used for discount entries when processing payments with write-offs'
    )