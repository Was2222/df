from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FleetVehicleEquipmentType(models.Model):
    _name = 'fleet.vehicle.equipment.type'
    _description = 'Type équipement véhicule'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string="Nom", required=True)

    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Produit lié",
        readonly=True,
        copy=False,
        ondelete='set null'
    )

    equipment_ids = fields.One2many(
        'fleet.vehicle.equipment',
        'equipment_type_id',
        string="Équipements"
    )

    equipment_count = fields.Integer(
        string="Nombre équipements",
        compute='_compute_equipment_count'
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        required=False,
        ondelete='set null'
    )
    def _compute_equipment_count(self):
        for rec in self:
            rec.equipment_count = len(rec.equipment_ids)

    def _prepare_product_vals(self):
        self.ensure_one()
        return {
            'name': rec_name(self),
            'type': 'consu',
            'sale_ok': False,
            'purchase_ok': True,
            'is_fleet_equipment_product': True,
            'fleet_equipment_type_id': self.id,
        }

    def _create_linked_product(self):
        self.ensure_one()

        if self.env.context.get('install_mode'):
            return

        product = self.env['product.template'].with_context(
            skip_product_bidirectional_sync=True
        ).create(self._prepare_product_vals())

        self.with_context(skip_equipment_type_product_sync=True).write({
            'product_tmpl_id': product.id
        })

    def _sync_linked_product(self):
        if self.env.context.get('install_mode'):
            return

        for rec in self:
            if not rec.product_tmpl_id:
                rec._create_linked_product()
            else:
                rec.product_tmpl_id.with_context(
                    skip_product_bidirectional_sync=True
                ).write(rec._prepare_product_vals())

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        if not self.env.context.get('skip_equipment_type_product_sync'):
            records._sync_linked_product()

        return records

    def write(self, vals):
        if self.env.context.get('skip_equipment_type_product_sync'):
            return super().write(vals)

        res = super().write(vals)
        self._sync_linked_product()
        return res

    def unlink(self):
        if self.env.context.get('skip_equipment_type_product_delete'):
            return super().unlink()

        for rec in self:
            if rec.equipment_ids:
                raise ValidationError(
                    _("Impossible de supprimer un type d’équipement lié à des équipements.")
                )

        linked_products = self.mapped('product_tmpl_id')
        res = super().unlink()

        if linked_products:
            linked_products.with_context(skip_product_linked_delete=True).unlink()

        return res

    def action_view_equipments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Équipements véhicule'),
            'res_model': 'fleet.vehicle.equipment',
            'view_mode': 'list,form',
            'domain': [('equipment_type_id', '=', self.id)],
            'context': {'default_equipment_type_id': self.id},
            'target': 'current',
        }


class FleetVehicleEquipment(models.Model):
    _name = 'fleet.vehicle.equipment'
    _description = 'Equipement véhicule'
    _order = 'purchase_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string="Nom",
        required=True,
        copy=False,
        default=lambda self: _('Nouveau')
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        required=True,
        ondelete='cascade'
    )

    equipment_type_id = fields.Many2one(
        'fleet.vehicle.equipment.type',
        string="Type d'équipement",
        required=True,
        ondelete='restrict'
    )

    serial_number = fields.Char(string="Numéro de série")
    purchase_date = fields.Date(string="Date d'achat")
    amount = fields.Float(string="Montant")

    state = fields.Selection([
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('hs', 'Hors service'),
    ], string="Statut", default='active', required=True)

    notes = fields.Text(string="Commentaire")

    user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Produit lié",
        readonly=True,
        copy=False,
        ondelete='set null'
    )

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )

    @api.onchange('vehicle_id', 'equipment_type_id')
    def _onchange_name(self):
        for rec in self:
            rec.name = rec._compute_equipment_name()

    def _compute_equipment_name(self):
        self.ensure_one()

        vehicle_name = ""
        if self.vehicle_id:
            vehicle_name = self.vehicle_id.name or self.vehicle_id.license_plate or ""

        equipment_name = self.equipment_type_id.name or _("Equipement")
        return f"{vehicle_name} - {equipment_name}" if vehicle_name else equipment_name

    def _prepare_product_vals(self):
        self.ensure_one()

        return {
            'name': self._compute_equipment_name(),
            'type': 'consu',
            'sale_ok': False,
            'purchase_ok': True,
            'standard_price': self.amount or 0.0,
            'list_price': self.amount or 0.0,
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
            'fleet_vehicle_equipment_id': self.id,
            'fleet_equipment_type_id': self.equipment_type_id.id if self.equipment_type_id else False,
            'is_fleet_equipment_product': True,
        }

    def _create_linked_product(self):
        self.ensure_one()

        if self.env.context.get('install_mode'):
            return

        product = self.env['product.template'].with_context(
            skip_product_bidirectional_sync=True
        ).create(self._prepare_product_vals())

        self.with_context(skip_equipment_product_sync=True).write({
            'product_tmpl_id': product.id
        })

    def _sync_linked_product(self):
        if self.env.context.get('install_mode'):
            return

        for rec in self:
            if not rec.product_tmpl_id:
                rec._create_linked_product()
            else:
                rec.product_tmpl_id.with_context(
                    skip_product_bidirectional_sync=True
                ).write(rec._prepare_product_vals())

    @api.constrains('vehicle_id', 'equipment_type_id')
    def _check_unique_equipment_per_vehicle_type(self):
        for rec in self:
            if not rec.vehicle_id or not rec.equipment_type_id:
                continue

            existing = self.search_count([
                ('id', '!=', rec.id),
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('equipment_type_id', '=', rec.equipment_type_id.id),
            ])

            if existing:
                raise ValidationError(
                    _("Ce véhicule possède déjà un équipement de ce type.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            if not rec.name or rec.name == _('Nouveau'):
                rec.with_context(skip_equipment_product_sync=True).write({
                    'name': rec._compute_equipment_name()
                })

        if not self.env.context.get('skip_equipment_product_sync'):
            records._sync_linked_product()

        return records

    def write(self, vals):
        if self.env.context.get('skip_equipment_product_sync'):
            return super().write(vals)

        res = super().write(vals)

        for rec in self:
            new_name = rec._compute_equipment_name()
            if rec.name != new_name:
                rec.with_context(skip_equipment_product_sync=True).write({
                    'name': new_name
                })

        self._sync_linked_product()
        return res

    def unlink(self):
        if self.env.context.get('skip_equipment_product_delete'):
            return super().unlink()

        linked_products = self.mapped('product_tmpl_id')
        res = super().unlink()

        if linked_products:
            linked_products.with_context(skip_product_linked_delete=True).unlink()

        return res

    def action_open_linked_product(self):
        self.ensure_one()

        if not self.product_tmpl_id:
            self._create_linked_product()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Produit lié'),
            'res_model': 'product.template',
            'res_id': self.product_tmpl_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


def rec_name(record):
    return record.name or _("Equipement")