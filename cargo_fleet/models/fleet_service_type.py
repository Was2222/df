from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fleet_service_type_id = fields.Many2one(
        'fleet.service.type',
        string="Type de service flotte",
        ondelete='set null',
        copy=False
    )

    fleet_equipment_type_id = fields.Many2one(
        'fleet.vehicle.equipment.type',
        string="Type d'équipement flotte",
        ondelete='set null',
        copy=False
    )

    fleet_vehicle_equipment_id = fields.Many2one(
        'fleet.vehicle.equipment',
        string="Équipement véhicule",
        ondelete='set null',
        copy=False
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        ondelete='set null',
        copy=False
    )

    is_fleet_service_product = fields.Boolean(
        string="Produit service flotte",
        default=False,
        copy=False
    )

    is_fleet_equipment_product = fields.Boolean(
        string="Produit équipement flotte",
        default=False,
        copy=False
    )


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        required=False,
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Produit lié",
        readonly=True,
        copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            if rec.service_type_id and not rec.product_tmpl_id:
                vehicle_name = ""
                if rec.vehicle_id:
                    vehicle_name = rec.vehicle_id.name or rec.vehicle_id.license_plate or ""

                service_name = rec.service_type_id.name or "Service"
                product_name = f"{vehicle_name} - {service_name}" if vehicle_name else service_name
                amount = rec.amount or 0.0

                product = self.env['product.template'].create({
                    'name': product_name,
                    'type': 'service',
                    'sale_ok': False,
                    'purchase_ok': True,
                    'vehicle_id': rec.vehicle_id.id if rec.vehicle_id else False,
                    'fleet_service_type_id': rec.service_type_id.id,
                    'is_fleet_service_product': True,
                    'list_price': amount,
                    'standard_price': amount,
                })

                rec.product_tmpl_id = product.id

        return records

    def write(self, vals):
        if self.env.context.get('skip_service_product_sync'):
            return super().write(vals)

        res = super().write(vals)

        for rec in self:
            if rec.product_tmpl_id and rec.service_type_id:
                vehicle_name = ""
                if rec.vehicle_id:
                    vehicle_name = rec.vehicle_id.name or rec.vehicle_id.license_plate or ""

                service_name = rec.service_type_id.name or "Service"
                product_name = f"{vehicle_name} - {service_name}" if vehicle_name else service_name
                amount = rec.amount or 0.0

                rec.product_tmpl_id.with_context(skip_product_bidirectional_sync=True).write({
                    'name': product_name,
                    'type': 'service',
                    'sale_ok': False,
                    'purchase_ok': True,
                    'vehicle_id': rec.vehicle_id.id if rec.vehicle_id else False,
                    'fleet_service_type_id': rec.service_type_id.id,
                    'is_fleet_service_product': True,
                    'list_price': amount,
                    'standard_price': amount,
                })

        return res

    def unlink(self):
        if self.env.context.get('skip_service_product_delete'):
            return super().unlink()

        linked_products = self.mapped('product_tmpl_id')
        res = super().unlink()

        if linked_products:
            linked_products.with_context(skip_product_linked_delete=True).unlink()

        return res


class FleetServiceType(models.Model):
    _inherit = 'fleet.service.type'

    category = fields.Selection([
        ('document', 'Document administratif'),
        ('service', 'Service'),
    ], string="Catégorie", default='service', required=True)

    service_code = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('vignette', 'Vignette'),
        ('visite_technique', 'Visite technique'),
        ('assurance', 'Assurance'),
        ('jawaz', 'Jawaz'),
        ('carburant', 'Carburant'),
        ('carte_verte', 'Carte verte'),
        ('immatriculation', 'Frais immatriculation'),
        ('penalite', 'Pénalités'),
        ('permis_circulation', 'Permis de circulation'),
        ('carte_grise', 'Carte grise'),
    ], string="Code service", required=True)

    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Produit lié",
        readonly=True,
        copy=False
    )

    def _prepare_service_product_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': True,
            'fleet_service_type_id': self.id,
            'is_fleet_service_product': True,
            'list_price': 0.0,
            'standard_price': 0.0,
        }

    def _ensure_linked_product(self):
        ProductTemplate = self.env['product.template']

        for rec in self:
            if not rec.id:
                continue

            if rec.product_tmpl_id:
                rec.product_tmpl_id.with_context(skip_product_bidirectional_sync=True).write({
                    'name': rec.name,
                    'type': 'service',
                    'sale_ok': False,
                    'purchase_ok': True,
                    'fleet_service_type_id': rec.id,
                    'is_fleet_service_product': True,
                })
                continue

            existing_product = ProductTemplate.search([
                ('fleet_service_type_id', '=', rec.id)
            ], limit=1)

            if existing_product:
                existing_product.with_context(skip_product_bidirectional_sync=True).write({
                    'name': rec.name,
                    'type': 'service',
                    'sale_ok': False,
                    'purchase_ok': True,
                    'fleet_service_type_id': rec.id,
                    'is_fleet_service_product': True,
                })
                rec.product_tmpl_id = existing_product.id
                continue

            product = ProductTemplate.create(rec._prepare_service_product_vals())
            rec.product_tmpl_id = product.id

    @api.model
    def _ensure_default_fleet_service_types(self):
        default_services = [
            {'name': 'Maintenance', 'category': 'service', 'service_code': 'maintenance'},
            {'name': 'Vignette', 'category': 'document', 'service_code': 'vignette'},
            {'name': 'Visite technique', 'category': 'document', 'service_code': 'visite_technique'},
            {'name': 'Assurance', 'category': 'document', 'service_code': 'assurance'},
            {'name': 'Jawaz', 'category': 'service', 'service_code': 'jawaz'},
            {'name': 'Carburant', 'category': 'service', 'service_code': 'carburant'},
            {'name': 'Carte verte', 'category': 'document', 'service_code': 'carte_verte'},
            {'name': 'Frais immatriculation', 'category': 'document', 'service_code': 'immatriculation'},
            {'name': 'Pénalités', 'category': 'service', 'service_code': 'penalite'},
            {'name': 'Permis de circulation', 'category': 'document', 'service_code': 'permis_circulation'},
            {'name': 'Carte grise', 'category': 'document', 'service_code': 'carte_grise'},
        ]

        for vals in default_services:
            service_type = self.search([
                ('service_code', '=', vals['service_code'])
            ], limit=1)

            if not service_type:
                service_type = self.create(vals)
            else:
                service_type.write({
                    'name': vals['name'],
                    'category': vals['category'],
                })

            service_type._ensure_linked_product()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        if not self.env.context.get('skip_service_type_product_sync'):
            records._ensure_linked_product()

        return records

    def write(self, vals):
        if self.env.context.get('skip_service_type_product_sync'):
            return super().write(vals)

        res = super().write(vals)
        self._ensure_linked_product()
        return res

    def unlink(self):
        if self.env.context.get('skip_service_type_product_delete'):
            return super().unlink()

        linked_products = self.mapped('product_tmpl_id')
        res = super().unlink()

        if linked_products:
            linked_products.with_context(skip_product_linked_delete=True).unlink()

        return res

    def init(self):
        self._ensure_default_fleet_service_types()