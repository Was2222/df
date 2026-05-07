from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        copy=False
    )

    fleet_service_type_id = fields.Many2one(
        'fleet.service.type',
        string="Type de service",
        copy=False
    )

    is_fleet_service_product = fields.Boolean(
        string="Produit Fleet Service",
        default=False,
        copy=False
    )

    fleet_equipment_type_id = fields.Many2one(
        'fleet.vehicle.equipment.type',
        string="Type d'équipement",
        copy=False
    )

    fleet_vehicle_equipment_id = fields.Many2one(
        'fleet.vehicle.equipment',
        string="Équipement véhicule",
        copy=False
    )

    is_fleet_equipment_product = fields.Boolean(
        string="Produit Fleet Équipement",
        default=False,
        copy=False
    )

    vehicle_brand_name = fields.Char(
        string="Marque véhicule",
        copy=False
    )

    vehicle_model_name = fields.Char(
        string="Modèle véhicule",
        copy=False
    )

    vehicle_amount_ht = fields.Float(
        string="Montant HT véhicule",
        copy=False
    )

    vehicle_tva = fields.Float(
        string="TVA véhicule",
        copy=False
    )

    vehicle_amount_ttc = fields.Float(
        string="Montant TTC véhicule",
        copy=False
    )

    @api.onchange('vehicle_id', 'fleet_service_type_id', 'fleet_equipment_type_id')
    def _onchange_fleet_name(self):
        for rec in self:
            vehicle_name = rec.vehicle_id.name or rec.vehicle_id.license_plate or "Véhicule"

            if rec.vehicle_id and rec.fleet_service_type_id:
                service_name = rec.fleet_service_type_id.name or "Service"
                rec.name = f"{vehicle_name} - {service_name}"

            elif rec.vehicle_id and rec.fleet_equipment_type_id:
                equipment_name = rec.fleet_equipment_type_id.name or "Équipement"
                rec.name = f"{vehicle_name} - {equipment_name}"

    @api.onchange('type')
    def _onchange_type_no_combo(self):
        for rec in self:
            if rec.type == 'combo':
                rec.type = 'service'
                return {
                    'warning': {
                        'title': 'Type interdit',
                        'message': 'Le type Combo est interdit. Le type a été remis à Service.',
                    }
                }

    @api.constrains('type')
    def _check_no_combo(self):
        for rec in self:
            if rec.type == 'combo':
                raise ValidationError("Le type Combo est interdit.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('type') == 'combo':
                vals['type'] = 'service'

            if vals.get('fleet_service_type_id'):
                vals['type'] = 'service'
                vals['sale_ok'] = False
                vals['purchase_ok'] = True
                vals['is_fleet_service_product'] = True

            if vals.get('fleet_equipment_type_id') or vals.get('fleet_vehicle_equipment_id') or vals.get('is_fleet_equipment_product'):
                vals['type'] = 'consu'
                vals['sale_ok'] = False
                vals['purchase_ok'] = True
                vals['is_fleet_equipment_product'] = True

        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('skip_product_bidirectional_sync'):
            return super().write(vals)

        local_vals = dict(vals)

        if local_vals.get('type') == 'combo':
            local_vals['type'] = 'service'

        if local_vals.get('fleet_service_type_id'):
            local_vals['type'] = 'service'
            local_vals['sale_ok'] = False
            local_vals['purchase_ok'] = True
            local_vals['is_fleet_service_product'] = True

        if local_vals.get('fleet_equipment_type_id') or local_vals.get('fleet_vehicle_equipment_id') or local_vals.get('is_fleet_equipment_product'):
            local_vals['type'] = 'consu'
            local_vals['sale_ok'] = False
            local_vals['purchase_ok'] = True
            local_vals['is_fleet_equipment_product'] = True

        res = super().write(local_vals)

        FleetVehicleLogServices = self.env['fleet.vehicle.log.services']
        FleetVehicle = self.env['fleet.vehicle']
        FleetServiceType = self.env['fleet.service.type']
        FleetVehicleEquipmentType = self.env['fleet.vehicle.equipment.type']
        FleetVehicleEquipment = self.env['fleet.vehicle.equipment']

        for rec in self:
            linked_services = FleetVehicleLogServices.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_services:
                service_vals = {}

                if 'fleet_service_type_id' in local_vals:
                    service_vals['service_type_id'] = rec.fleet_service_type_id.id if rec.fleet_service_type_id else False

                if 'vehicle_id' in local_vals:
                    service_vals['vehicle_id'] = rec.vehicle_id.id if rec.vehicle_id else False

                if 'list_price' in local_vals and 'amount' in FleetVehicleLogServices._fields:
                    service_vals['amount'] = rec.list_price or 0.0

                if service_vals:
                    linked_services.with_context(skip_service_product_sync=True).write(service_vals)

            linked_service_types = FleetServiceType.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_service_types:
                service_type_vals = {}
                if 'name' in local_vals:
                    service_type_vals['name'] = rec.name

                if service_type_vals:
                    linked_service_types.with_context(skip_service_type_product_sync=True).write(service_type_vals)

            linked_vehicles = FleetVehicle.search([
                ('product_template_id', '=', rec.id)
            ])
            if linked_vehicles:
                vehicle_vals = {}

                if 'vehicle_amount_ht' in local_vals:
                    vehicle_vals['amount_ht'] = rec.vehicle_amount_ht or 0.0

                if 'vehicle_tva' in local_vals:
                    vehicle_vals['tva'] = rec.vehicle_tva or 0.0

                if vehicle_vals:
                    linked_vehicles.with_context(skip_vehicle_product_sync=True).write(vehicle_vals)

            linked_equipment_types = FleetVehicleEquipmentType.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_equipment_types:
                eq_type_vals = {}
                if 'name' in local_vals:
                    eq_type_vals['name'] = rec.name

                if eq_type_vals:
                    linked_equipment_types.with_context(skip_equipment_type_product_sync=True).write(eq_type_vals)

            linked_equipments = FleetVehicleEquipment.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_equipments:
                equipment_vals = {}

                if 'fleet_equipment_type_id' in local_vals:
                    equipment_vals['equipment_type_id'] = rec.fleet_equipment_type_id.id if rec.fleet_equipment_type_id else False

                if 'vehicle_id' in local_vals:
                    equipment_vals['vehicle_id'] = rec.vehicle_id.id if rec.vehicle_id else False

                if 'list_price' in local_vals:
                    equipment_vals['amount'] = rec.list_price or 0.0

                if equipment_vals:
                    linked_equipments.with_context(skip_equipment_product_sync=True).write(equipment_vals)

        return res

    def unlink(self):
        if self.env.context.get('skip_product_linked_delete'):
            return super().unlink()

        FleetVehicle = self.env['fleet.vehicle']
        FleetServiceLog = self.env['fleet.vehicle.log.services']
        FleetServiceType = self.env['fleet.service.type']
        FleetVehicleEquipmentType = self.env['fleet.vehicle.equipment.type']
        FleetVehicleEquipment = self.env['fleet.vehicle.equipment']

        for rec in self:
            linked_services = FleetServiceLog.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_services:
                linked_services.with_context(skip_service_product_delete=True).unlink()

            linked_service_types = FleetServiceType.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_service_types:
                linked_service_types.with_context(skip_service_type_product_delete=True).unlink()

            linked_vehicles = FleetVehicle.search([
                ('product_template_id', '=', rec.id)
            ])
            if linked_vehicles:
                linked_vehicles.with_context(skip_vehicle_product_delete=True).unlink()

            linked_equipment_types = FleetVehicleEquipmentType.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_equipment_types:
                linked_equipment_types.with_context(skip_equipment_type_product_delete=True).unlink()

            linked_equipments = FleetVehicleEquipment.search([
                ('product_tmpl_id', '=', rec.id)
            ])
            if linked_equipments:
                linked_equipments.with_context(skip_equipment_product_delete=True).unlink()

        return super().unlink()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_fleet_purchase_filter_domain(self):
        ctx = self.env.context
        vehicle_purchase_type = ctx.get('fleet_vehicle_purchase_type')
        service_code = ctx.get('fleet_purchase_service_code')
        vehicle_id = ctx.get('fleet_vehicle_id')

        domain = [('purchase_ok', '=', True)]

        if vehicle_purchase_type in ('contract', 'leasing_contract'):
            if vehicle_id:
                domain.append(('product_tmpl_id.vehicle_id', '=', vehicle_id))
            else:
                domain.append(('id', '=', 0))

        elif vehicle_purchase_type == 'expense':
            if service_code:
                domain.append(('product_tmpl_id.fleet_service_type_id.service_code', '=', service_code))

        return domain

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])

        if self.env.context.get('fleet_filter_purchase_products'):
            args += self._get_fleet_purchase_filter_domain()

        return super().name_search(name, args, operator, limit)