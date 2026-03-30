from odoo import models, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('location_id', 'location_dest_id')
    def _check_locations_not_equal(self):
        for picking in self:
            if (
                picking.location_id
                and picking.location_dest_id
                and picking.location_id.id == picking.location_dest_id.id
            ):
                raise ValidationError(_(
                    "Source Location and Destination Location cannot be the same."
                ))