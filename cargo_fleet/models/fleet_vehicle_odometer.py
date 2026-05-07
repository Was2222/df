from odoo import models, fields, api


class FleetVehicleOdometer(models.Model):
    _name = 'fleet.vehicle.odometer.custom'
    _description = 'Suivi kilométrage véhicule'
    _order = 'date desc, id desc'
    _rec_name = 'vehicle_id'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Véhicule',
        required=True,
        ondelete='cascade'
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )

    kilometrage = fields.Float(
        string='Kilométrage',
        required=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Utilisateur',
        default=lambda self: self.env.user,
        readonly=True
    )

    driver_id = fields.Many2one(
        'res.partner',
        string='Conducteur',
        related='vehicle_id.driver_id',
        store=True,
        readonly=True
    )

    immatriculation = fields.Char(
        string='Immatriculation',
        related='vehicle_id.license_plate',
        store=True,
        readonly=True
    )

    marque_nom = fields.Char(
        string='Marque',
        compute='_compute_vehicle_infos',
        store=True,
        readonly=True
    )

    modele_nom = fields.Char(
        string='Modèle',
        compute='_compute_vehicle_infos',
        store=True,
        readonly=True
    )

    categorie_nom = fields.Char(
        string='Catégorie',
        compute='_compute_vehicle_infos',
        store=True,
        readonly=True
    )

    name = fields.Char(
        string='Référence',
        compute='_compute_name',
        store=True
    )

    @api.depends(
        'vehicle_id',
        'vehicle_id.model_id',
        'vehicle_id.model_id.name',
        'vehicle_id.model_id.brand_id',
        'vehicle_id.model_id.brand_id.name',
        'vehicle_id.category_id',
        'vehicle_id.category_id.name'
    )
    def _compute_vehicle_infos(self):
        for rec in self:
            rec.marque_nom = rec.vehicle_id.model_id.brand_id.name if rec.vehicle_id and rec.vehicle_id.model_id and rec.vehicle_id.model_id.brand_id else ''
            rec.modele_nom = rec.vehicle_id.model_id.name if rec.vehicle_id and rec.vehicle_id.model_id else ''
            rec.categorie_nom = rec.vehicle_id.category_id.name if rec.vehicle_id and rec.vehicle_id.category_id else ''

    @api.depends('vehicle_id', 'date', 'kilometrage')
    def _compute_name(self):
        for rec in self:
            vehicle_name = rec.vehicle_id.name or rec.vehicle_id.license_plate or 'Véhicule'
            rec.name = f"{vehicle_name} - {rec.date or ''} - {rec.kilometrage or 0}"