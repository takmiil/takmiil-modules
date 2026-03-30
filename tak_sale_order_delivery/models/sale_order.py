from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    outgoing_picking_count = fields.Integer(string="Outgoing Pickings", compute="_compute_outgoing_picking_count")

    @api.depends("picking_ids", "picking_ids.state", "picking_ids.picking_type_id.code")
    def _compute_outgoing_picking_count(self):
        for order in self:
            outgoing_pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_id.code == "outgoing"
                and p.state not in ("done", "cancel")
            )
            order.outgoing_picking_count = len(outgoing_pickings)

    def action_validate_all_deliveries(self):
        self.ensure_one()

        if not self.env.user.has_group("stock.group_stock_user"):
            raise AccessError("You don't have permission to validate deliveries.")

        outgoing_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "outgoing"
            and p.state not in ("done", "cancel")
        )

        if not outgoing_pickings:
            raise UserError("No delivery orders found for this sale order.")

        for picking in outgoing_pickings:
            picking.action_assign()


        ready_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "outgoing" and p.state == "assigned"
        )

        if not ready_pickings:
            raise UserError("All delivery orders are waiting for inventory. Please check stock availability.")

        
        needs_backorder = False
        for picking in ready_pickings:
            for move in picking.move_ids:
                if move.product_id.is_storable and move.product_uom_qty > move.quantity:
                    needs_backorder = True
                    break
            if needs_backorder:
                break

        if needs_backorder:
            return self._trigger_backorder_wizard(ready_pickings)


        for picking in ready_pickings:
            try:
                picking.button_validate()
            except Exception as e:
                raise UserError(_("Error validating %s: %s") % (picking.name, str(e)))

        return True

    def _trigger_backorder_wizard(self, pickings):
        view_id = self.env.ref(
            "stock.view_backorder_confirmation", raise_if_not_found=False
        )
        if not view_id:
            raise UserError(
                _("Backorder view not found. Please contact administrator.")
            )

        ctx = {
            "button_validate_picking_ids": pickings.ids,
            "default_show_transfers": len(pickings) > 1,
            "default_pick_ids": [(6, 0, pickings.ids)],
        }

        return {
            "name": _("Create Backorder?"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.backorder.confirmation",
            "views": [(view_id.id, "form")],
            "view_id": view_id.id,
            "target": "new",
            "context": ctx,
        }
