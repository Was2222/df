# -*- coding: utf-8 -*-
# =============================================================================
# fleet_rental_crm / wizard / rejection_wizard.py
# =============================================================================

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RentalRejectionWizard(models.TransientModel):
    _name = 'rental.rejection.wizard'
    _description = 'Wizard de motif de rejet'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Devis",
        required=True,
    )

    rejection_reason = fields.Text(
        string="Motif du rejet",
        required=True,
        help="Veuillez indiquer la raison du rejet du devis",
    )

    def action_confirm_rejection(self):
        """Confirme le rejet avec le motif saisi"""
        self.ensure_one()
        
        if not self.rejection_reason:
            raise UserError(_("Veuillez indiquer un motif de rejet."))
        
        # Appeler la méthode de rejet sur le devis
        self.sale_order_id._do_reject(self.rejection_reason)
        
        return {'type': 'ir.actions.act_window_close'}