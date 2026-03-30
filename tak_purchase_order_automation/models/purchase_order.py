from odoo import api, fields, models, exceptions

import logging
_logger = logging.getLogger(__name__)



class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    def button_confirm(self):
        res = super(PurchaseOrder, self.with_context(default_immediate_transfer=True)).button_confirm()
        for order in self:
            warehouse = order.picking_type_id.warehouse_id
            if warehouse.is_receipt_set_to_done and order.picking_ids: 
                for picking in self.picking_ids:
                    if picking.state == 'cancel':
                        continue
                    for move in picking.move_ids:
                        move.quantity = move.product_qty
                    picking._autoconfirm_picking()
                    picking.button_validate()
                    for move_line in picking.move_ids_without_package:
                        move_line.quantity = move_line.product_uom_qty
                    
                    for mv_line in picking.move_ids.mapped('move_line_ids'):
                        # if not mv_line.button_validate and mv_line.reserved_qty or mv_line.reserved_uom_qty:
                        mv_line.quantity = mv_line.quantity_product_uom#.reserved_qty or mv_line.reserved_uom_qty

                    picking._action_done()

            if warehouse.create_bill and not order.invoice_ids:
                order.action_create_invoice()
            if warehouse.validate_bill and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.invoice_date = invoice.date
                    invoice.action_post()

        return res  
