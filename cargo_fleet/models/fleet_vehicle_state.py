from odoo import models, api


class FleetVehicleState(models.Model):
    _inherit = 'fleet.vehicle.state'

    @api.model
    def _remove_default_states(self):
        xml_ids = [
            'fleet.fleet_vehicle_state_new_request',
            'fleet.fleet_vehicle_state_to_order',
            'fleet.fleet_vehicle_state_registered',
            'fleet.fleet_vehicle_state_downgraded',
        ]

        for xmlid in xml_ids:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if record:
                record.unlink()

    @api.model
    def init(self):
        self._remove_default_states()