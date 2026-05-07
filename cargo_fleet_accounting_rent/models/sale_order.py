from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        domain="[('state_id.name', '=', 'Bloqué')]",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        vehicle_id = self.env.context.get('default_vehicle_id')
        if vehicle_id:
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id).exists()
            if vehicle:
                res['vehicle_id'] = vehicle.id

        return res

    @api.constrains('vehicle_id')
    def _check_vehicle_must_be_blocked(self):
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.state_id.name != 'Bloqué':
                raise ValidationError(_("Seuls les véhicules bloqués peuvent être sélectionnés en vente."))

    def write(self, vals):
        if 'vehicle_id' in vals and not self.env.context.get('allow_vehicle_sale_edit'):
            raise ValidationError(_("Le véhicule n’est pas modifiable."))
        return super().write(vals)