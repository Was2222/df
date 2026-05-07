from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        domain="[('state_id.name', '=', 'Bloqué')]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        vehicle_id = self.env.context.get('default_vehicle_id')
        if not vehicle_id and self.env.context.get('active_model') == 'fleet.vehicle':
            vehicle_id = self.env.context.get('active_id')

        if vehicle_id:
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
            if vehicle.exists():
                res['vehicle_id'] = vehicle.id

        return res

    @api.constrains('vehicle_id')
    def _check_vehicle_must_be_blocked(self):
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.state_id.name != 'Bloqué':
                raise ValidationError(_("Seuls les véhicules bloqués peuvent être sélectionnés en vente."))

    def _prepare_vehicle_sale_invoice_policy(self):
        for order in self:
            if order.vehicle_id and not order.is_rental_order:
                for line in order.order_line:
                    if line.product_id:
                        line.product_id.product_tmpl_id.write({
                            'invoice_policy': 'order',
                        })

    def action_confirm(self):
        self._prepare_vehicle_sale_invoice_policy()
        return super().action_confirm()

    def action_confirm_vehicle_sale(self):
        self._prepare_vehicle_sale_invoice_policy()
        return self.action_confirm()

    def action_create_vehicle_invoice(self):
        for order in self:
            if not order.vehicle_id:
                raise ValidationError(_("Cette commande n'est pas liée à un véhicule."))

            if order.state not in ('sale', 'done'):
                raise ValidationError(_("Veuillez confirmer la vente avant de créer la facture."))

        invoices = self._create_invoices()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture client'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoices.id if len(invoices) == 1 else False,
            'domain': [('id', 'in', invoices.ids)],
            'target': 'current',
        }

    def write(self, vals):
        if 'vehicle_id' in vals and not self.env.context.get('allow_vehicle_sale_edit'):
            raise ValidationError(_("Le véhicule n’est pas modifiable."))
        return super().write(vals)