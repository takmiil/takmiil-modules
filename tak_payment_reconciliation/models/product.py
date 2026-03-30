# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError



class ProductTemplate(models.Model):
    _inherit = "product.template"

    customer_discount_product = fields.Boolean(string="Is Sale Discount", default=False)
    vendor_discount_product = fields.Boolean(string="Is Purchase Discount", default=False)
    
    
    
    @api.onchange('customer_discount_product', 'vendor_discount_product')
    def _onchange_discount_fields(self):
        for rec in self:
            if rec.customer_discount_product and rec.vendor_discount_product:
                raise ValidationError("You can only Select One Discount Option!")
            
    
    
