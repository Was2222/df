from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def force_fleet_menu_labels_fr(self):
        menu_labels = {
            "fleet.fleet_vehicles": "Flotte",
            "fleet.fleet_vehicle_menu": "Véhicules",
            "fleet.fleet_vehicle_log_contract_menu": "Contrats leasing",
            "cargo_fleet.menu_vehicle_purchase_contracts": "Contrats d'achat",
        }

        for xmlid, label in menu_labels.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.with_context(lang="fr_FR").sudo().write({
                    "name": label
                })