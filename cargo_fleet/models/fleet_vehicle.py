from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    _sql_constraints = [
        (
            'vin_sn_unique',
            'unique(vin_sn)',
            'Le numéro de châssis doit être unique.'
        ),
    ]

    type_acquisition = fields.Selection([
        ('achat', 'Achat'),
        ('leasing', 'Leasing'),
    ], string="Type d’acquisition", required=True)

    date_mise_circulation = fields.Date(string="Date mise en circulation", required=True)
    vehicle_code = fields.Char(string="Code")
    cost_center = fields.Char(string="Centre de coût")
    order_number = fields.Char(string="Numéro d’ordre")
    registration_card = fields.Char(string="Carte grise")
    numero_w = fields.Char(string="Numéro W", required=True)
    key_code = fields.Char(string="Code clé")
    initial_odometer = fields.Float(string="Kilométrage initial")
    planned_return_date = fields.Date(string="Date prévue de restitution")
    initial_hour_index = fields.Float(string="Indexe horaire initial")
    purchase_date = fields.Date(string="Date d’achat", required=True)
    warranty = fields.Char(string="Garantie")
    amount_ht = fields.Float(string="Montant HT")

    amount_ttc = fields.Float(
        string="Montant TTC",
        compute="_compute_amount_ttc",
        store=True
    )

    tax_id = fields.Many2one('account.tax', string="Taxe")

    model_name = fields.Char(
        string="Modèle",
        related="model_id.name",
        store=True
    )

    dealer_id = fields.Many2one('res.partner', string="Fournisseur", required=True)

    product_account_number = fields.Char(string="Numéro compte produit")
    leasing_account_number = fields.Char(string="Numéro compte leasing")
    fleet_name = fields.Char(string="Flotte")

    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('gasoline', 'Essence'),
        ('hybrid', 'Hybride'),
        ('electric', 'Electrique'),
        ('lpg', 'GPL'),
        ('other', 'Autre'),
    ], string="Energie")

    vehicle_genre = fields.Selection([
        ('choisir', 'Choisir'),
        ('fg_vitree_avec_sieges', 'FG VITREE AVEC SIEGES'),
        ('conduite_interieure', 'Conduite intérieure'),
        ('station_wagon', 'STATION WAGON'),
        ('fourgon', 'FOURGON'),
        ('fourgon_tole', 'FOURGON TOLE'),
        ('hybride', 'HYBRIDE'),
        ('essence_electrique', 'ESSENCE ELECTRIQUE'),
        ('fgtte', 'FGTTE'),
        ('fourgonnette_vitree_avec_siege', 'FOURGONNETTE VITREE AVEC SIEGE'),
        ('quadricycle', 'QUADRICYCLE'),
        ('chassis_cabine', 'CHASSIS CABINE'),
        ('camion_cabine', 'CAMION CABINE'),
        ('arkana', 'ARKANA'),
    ], string="Genre", default='choisir')
    rental_contract_count = fields.Integer(
        string="Nombre contrats location",
        compute="_compute_rental_contract_count"
    )
    service_name = fields.Selection([
        ('choisir', 'Choisir'),
        ('informatique', 'Informatique'),
        ('location', 'Location'),
    ], string="Service", default='choisir')

    driver_activity = fields.Char(string="Activité")

    main_attachment = fields.Binary(string="Attachement")
    main_attachment_filename = fields.Char(string="Nom attachement")

    brand_name = fields.Char(
        string="Marque",
        compute="_compute_brand_name",
        store=True
    )

    vehicle_category = fields.Char(
        string="Catégorie",
        compute="_compute_vehicle_category",
        store=True
    )

    attachment_count_custom = fields.Integer(
        string="Attachement",
        compute="_compute_attachment_count_custom"
    )

    date_added = fields.Datetime(
        string="Date d’ajout",
        readonly=True,
        default=fields.Datetime.now
    )

    purchase_contract_ids = fields.One2many(
        'purchase.order',
        'vehicle_id',
        string="Contrats achat",
        domain=[('vehicle_purchase_type', '=', 'contract')]
    )

    leasing_contract_ids = fields.One2many(
        'purchase.order',
        'vehicle_id',
        string="Contrats leasing",
        domain=[('vehicle_purchase_type', '=', 'leasing_contract')]
    )

    purchase_expense_ids = fields.One2many(
        'purchase.order',
        'vehicle_id',
        string="Dépenses véhicule",
        domain=[('vehicle_purchase_type', '=', 'expense')]
    )

    purchase_contract_count = fields.Integer(
        string="Nombre contrats achat",
        compute="_compute_purchase_contract_count"
    )

    leasing_contract_count = fields.Integer(
        string="Nombre contrats leasing",
        compute="_compute_leasing_contract_count"
    )

    purchase_expense_count = fields.Integer(
        string="Nombre dépenses véhicule",
        compute="_compute_purchase_expense_count"
    )

    sale_order_ids = fields.One2many(
        'sale.order',
        'vehicle_id',
        string="Contrats vente / location"
    )

    sale_order_count = fields.Integer(
        string="Nombre ventes",
        compute="_compute_sale_order_count"
    )

    product_id = fields.Many2one(
        'product.product',
        string="Produit lié",
        readonly=True,
        copy=False,
        ondelete='restrict'
    )

    product_template_id = fields.Many2one(
        'product.template',
        string="Template produit",
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True
    )

    administrative_document_ids = fields.One2many(
        'fleet.vehicle.document',
        'vehicle_id',
        string="Documents administratifs"
    )

    administrative_document_count = fields.Integer(
        string="Nombre documents",
        compute="_compute_administrative_document_count"
    )

    registration_doc_ids = fields.One2many(
        'fleet.vehicle.document',
        'vehicle_id',
        string="Cartes grises",
        domain=[('document_type', '=', 'carte_grise')]
    )

    circulation_permit_doc_ids = fields.One2many(
        'fleet.vehicle.document',
        'vehicle_id',
        string="Permis de circulation",
        domain=[('document_type', '=', 'permis_circulation')]
    )

    vignette_doc_ids = fields.One2many(
        'fleet.vehicle.document',
        'vehicle_id',
        string="Vignettes",
        domain=[('document_type', '=', 'vignette')]
    )

    insurance_doc_ids = fields.One2many(
        'fleet.vehicle.document',
        'vehicle_id',
        string="Assurances",
        domain=[('document_type', '=', 'assurance')]
    )

    technical_visit_doc_ids = fields.One2many(
        'fleet.vehicle.document',
        'vehicle_id',
        string="Visites techniques",
        domain=[('document_type', '=', 'visite')]
    )

    documents_generated_on_payment = fields.Boolean(
        string="Documents générés",
        default=False,
        copy=False
    )

    vehicle_info_confirmed = fields.Boolean(
        string="Infos véhicule confirmées",
        default=False,
        copy=False
    )

    can_edit_vehicle = fields.Boolean(
        string="Modification autorisée",
        compute="_compute_can_edit_vehicle"
    )

    can_block_vehicle = fields.Boolean(
        string="Peut bloquer",
        compute="_compute_can_block_vehicle"
    )

    can_unblock_vehicle = fields.Boolean(
        string="Peut débloquer",
        compute="_compute_can_unblock_vehicle"
    )

    is_blocked_manual = fields.Boolean(
        string="Blocage manuel",
        default=False,
        copy=False
    )

    equipment_ids = fields.One2many(
        'fleet.vehicle.equipment',
        'vehicle_id',
        string="Équipements"
    )

    equipment_count = fields.Integer(
        string="Nombre équipements",
        compute="_compute_equipment_count"
    )

    penalite_expense_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'vehicle_id',
        string="Pénalités",
        domain=[('service_code', '=', 'penalite')]
    )

    penalite_count = fields.Integer(
        string="Nombre pénalités",
        compute="_compute_penalite_count"
    )

    account_move_line_ids = fields.Many2many(
        'account.move.line',
        compute='_compute_account_move_line_ids',
        string="Écritures comptables"
    )

    account_move_line_count = fields.Integer(
        string="Nombre écritures comptables",
        compute='_compute_account_move_line_ids'
    )

    assurance_first_name = fields.Char(string="Nom assurance")
    assurance_first_date_start = fields.Date(string="Date début assurance")
    assurance_first_date_end = fields.Date(string="Date fin assurance")
    assurance_first_state = fields.Selection([
        ('not_paid', 'Non payé'),
        ('paid', 'Payé'),
        ('expired', 'Expiré'),
    ], string="Statut assurance", default='not_paid')

    vignette_first_name = fields.Char(string="Nom vignette")
    vignette_first_date_start = fields.Date(string="Date début vignette")
    vignette_first_date_end = fields.Date(string="Date fin vignette")
    vignette_first_state = fields.Selection([
        ('not_paid', 'Non payé'),
        ('paid', 'Payé'),
        ('expired', 'Expiré'),
    ], string="Statut vignette", default='not_paid')

    visite_first_name = fields.Char(string="Nom visite technique")
    visite_first_date_start = fields.Date(string="Date début visite technique")
    visite_first_date_end = fields.Date(string="Date fin visite technique")
    visite_first_state = fields.Selection([
        ('not_paid', 'Non payé'),
        ('paid', 'Payé'),
        ('expired', 'Expiré'),
    ], string="Statut visite technique", default='not_paid')

    permis_first_name = fields.Char(string="Nom permis circulation")
    permis_first_date_start = fields.Date(string="Date début permis")
    permis_first_date_end = fields.Date(string="Date fin permis")
    permis_first_state = fields.Selection([
        ('not_paid', 'Non payé'),
        ('paid', 'Payé'),
        ('expired', 'Expiré'),
    ], string="Statut permis", default='not_paid')
    def _compute_rental_contract_count(self):
        RentalContract = self.env['car.rental.contract'].sudo()
        for rec in self:
            rec.rental_contract_count = RentalContract.search_count([
                '|',
                ('current_vehicle_id', '=', rec.id),
                ('contract_vehicle_ids.vehicle_id', '=', rec.id),
            ])


    def action_open_rental_contracts(self):
        self.ensure_one()

        contracts = self.env['car.rental.contract'].sudo().search([
            '|',
            ('current_vehicle_id', '=', self.id),
            ('contract_vehicle_ids.vehicle_id', '=', self.id),
        ])

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrats de location'),
            'res_model': 'car.rental.contract',
            'view_mode': 'list,form',
            'domain': [('id', 'in', contracts.ids)],
            'context': {
                'default_current_vehicle_id': self.id,
            },
            'target': 'current',
        }
    @api.depends('license_plate', 'numero_w', 'model_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                rec.license_plate
                or rec.numero_w
                or (rec.model_id.name if rec.model_id else False)
                or _("Véhicule")
            )

    @api.constrains('vin_sn')
    def _check_vin_sn_length(self):
        for rec in self:
            vin = (rec.vin_sn or '').strip()
            if not vin:
                raise ValidationError(_("Le numéro de châssis est obligatoire."))
            if len(vin) != 17:
                raise ValidationError(_("Le numéro de châssis doit contenir exactement 17 caractères."))

    @api.constrains('numero_w', 'model_id', 'type_acquisition', 'dealer_id', 'purchase_date', 'date_mise_circulation')
    def _check_required_vehicle_fields(self):
        for rec in self:
            if not (rec.numero_w or '').strip():
                raise ValidationError(_("Le numéro W est obligatoire."))
            if not rec.model_id:
                raise ValidationError(_("Le modèle est obligatoire."))
            if not rec.type_acquisition:
                raise ValidationError(_("Le type d’acquisition est obligatoire."))
            if not rec.dealer_id:
                raise ValidationError(_("Le fournisseur / concessionnaire est obligatoire."))
            if not rec.purchase_date:
                raise ValidationError(_("La date d’achat est obligatoire."))
            if not rec.date_mise_circulation:
                raise ValidationError(_("La date de mise en circulation est obligatoire."))

    @api.depends('amount_ht', 'tax_id')
    def _compute_amount_ttc(self):
        for rec in self:
            if rec.tax_id:
                taxes = rec.tax_id.compute_all(rec.amount_ht or 0.0)
                rec.amount_ttc = taxes['total_included']
            else:
                rec.amount_ttc = rec.amount_ht or 0.0

    @api.depends('model_id', 'model_id.brand_id', 'model_id.brand_id.name')
    def _compute_brand_name(self):
        for rec in self:
            rec.brand_name = rec.model_id.brand_id.name if rec.model_id and rec.model_id.brand_id else ''

    @api.depends('category_id', 'category_id.name')
    def _compute_vehicle_category(self):
        for rec in self:
            rec.vehicle_category = rec.category_id.name if rec.category_id else ''

    @api.depends('main_attachment')
    def _compute_attachment_count_custom(self):
        for rec in self:
            rec.attachment_count_custom = 1 if rec.main_attachment else 0

    def _compute_penalite_count(self):
        for rec in self:
            rec.penalite_count = len(rec.penalite_expense_ids)

    def _compute_equipment_count(self):
        for rec in self:
            rec.equipment_count = len(rec.equipment_ids)

    @api.depends('state_id')
    def _compute_can_edit_vehicle(self):
        for rec in self:
            rec.can_edit_vehicle = bool(rec.state_id and rec.state_id.name == 'En création')

    @api.depends('state_id')
    def _compute_can_block_vehicle(self):
        for rec in self:
            rec.can_block_vehicle = bool(rec.state_id and rec.state_id.name == 'Disponible')

    @api.depends('state_id')
    def _compute_can_unblock_vehicle(self):
        for rec in self:
            rec.can_unblock_vehicle = bool(rec.state_id and rec.state_id.name == 'Bloqué')

    def _compute_purchase_contract_count(self):
        PurchaseOrder = self.env['purchase.order']
        for rec in self:
            rec.purchase_contract_count = PurchaseOrder.search_count([
                ('vehicle_id', '=', rec.id),
                ('vehicle_purchase_type', '=', 'contract')
            ])

    def _compute_leasing_contract_count(self):
        PurchaseOrder = self.env['purchase.order']
        for rec in self:
            rec.leasing_contract_count = PurchaseOrder.search_count([
                ('vehicle_id', '=', rec.id),
                ('vehicle_purchase_type', '=', 'leasing_contract')
            ])

    def _compute_purchase_expense_count(self):
        PurchaseOrder = self.env['purchase.order']

        for rec in self:
            orders = PurchaseOrder.search([
                ('vehicle_purchase_type', '=', 'expense'),
                '|',
                ('vehicle_id', '=', rec.id),
                '|',
                ('assurance_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('vignette_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('visite_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('jawaz_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('carburant_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('carte_verte_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('immatriculation_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('penalite_vehicle_line_ids.vehicle_id', '=', rec.id),
                '|',
                ('permis_circulation_vehicle_line_ids.vehicle_id', '=', rec.id),
                ('carte_grise_vehicle_line_ids.vehicle_id', '=', rec.id),
            ])

            rec.purchase_expense_count = len(orders)

    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)

    def _compute_administrative_document_count(self):
        for rec in self:
            rec.administrative_document_count = len(rec.administrative_document_ids)

    def _compute_account_move_line_ids(self):
        MoveLine = self.env['account.move.line'].sudo()
        for rec in self:
            lines = MoveLine.browse()

            purchase_orders = rec.purchase_contract_ids | rec.leasing_contract_ids | rec.purchase_expense_ids
            sale_orders = rec.sale_order_ids

            if purchase_orders:
                lines |= MoveLine.search([
                    ('move_id.purchase_id', 'in', purchase_orders.ids),
                    ('display_type', '=', False),
                    ('move_id.state', '!=', 'cancel'),
                ])

            if sale_orders:
                lines |= MoveLine.search([
                    ('move_id.invoice_origin', 'in', sale_orders.mapped('name')),
                    ('display_type', '=', False),
                    ('move_id.state', '!=', 'cancel'),
                ])

            if rec.product_id:
                lines |= MoveLine.search([
                    ('product_id', '=', rec.product_id.id),
                    ('display_type', '=', False),
                    ('move_id.state', '!=', 'cancel'),
                ])

            rec.account_move_line_ids = lines.sorted(
                lambda l: ((l.date or fields.Date.today()), l.id),
                reverse=True
            )
            rec.account_move_line_count = len(rec.account_move_line_ids)

    def _prepare_product_template_vals(self):
        self.ensure_one()

        product_name = " - ".join(filter(None, [
            self.license_plate or self.numero_w,
            self.brand_name,
            self.model_id.name if self.model_id else False,
            self.vehicle_code,
        ])).strip() or "Véhicule"

        return {
            'name': product_name,
            'type': 'consu',
            'standard_price': self.amount_ht or 0.0,
            'list_price': self.amount_ttc or 0.0,
            'purchase_ok': True,
            'sale_ok': True,
            'purchase_method': 'purchase',
            'default_code': self.vehicle_code or self.license_plate or self.numero_w or False,
            'description_purchase': self.description or False,
            'vehicle_id': self.id,
            'vehicle_brand_name': self.brand_name or False,
            'vehicle_model_name': self.model_id.name if self.model_id else False,
            'vehicle_amount_ht': self.amount_ht or 0.0,
            'vehicle_amount_ttc': self.amount_ttc or 0.0,
            'taxes_id': [(6, 0, [self.tax_id.id])] if self.tax_id else False,
            'supplier_taxes_id': [(6, 0, [self.tax_id.id])] if self.tax_id else False,
        }

    def _create_or_update_supplierinfo(self):
        self.ensure_one()
        if not self.product_template_id or not self.dealer_id:
            return

        supplierinfo = self.env['product.supplierinfo'].search([
            ('product_tmpl_id', '=', self.product_template_id.id),
            ('partner_id', '=', self.dealer_id.id),
        ], limit=1)

        vals = {
            'partner_id': self.dealer_id.id,
            'product_tmpl_id': self.product_template_id.id,
            'price': self.amount_ht or 0.0,
        }

        if supplierinfo:
            supplierinfo.write(vals)
        else:
            self.env['product.supplierinfo'].create(vals)

    def _create_linked_product(self):
        self.ensure_one()
        template = self.env['product.template'].create(
            self._prepare_product_template_vals()
        )

        self.with_context(skip_vehicle_product_sync=True).write({
            'product_id': template.product_variant_id.id
        })

        self._create_or_update_supplierinfo()

    def _sync_linked_product(self):
        for rec in self:
            if not rec.product_id:
                rec._create_linked_product()
                continue

            rec.product_id.product_tmpl_id.with_context(
                skip_product_bidirectional_sync=True
            ).write(rec._prepare_product_template_vals())

            rec._create_or_update_supplierinfo()

    def _get_vehicle_document_ref(self):
        self.ensure_one()
        return self.license_plate or self.numero_w or self.display_name

    def _get_first_document_default_name(self, document_type):
        self.ensure_one()

        ref = self._get_vehicle_document_ref()

        labels = {
            'assurance': _("Assurance"),
            'vignette': _("Vignette"),
            'visite': _("Visite technique"),
            'permis_circulation': _("Permis de circulation"),
            'carte_grise': _("Carte grise"),
        }

        return f"{labels.get(document_type, _('Document'))} - {ref}"

    def _document_exists(self, document_type, date_start=False, date_end=False):
        self.ensure_one()

        domain = [
            ('vehicle_id', '=', self.id),
            ('document_type', '=', document_type),
        ]

        if date_start:
            domain.append(('date_start', '=', date_start))
        if date_end:
            domain.append(('date_end', '=', date_end))

        return bool(self.env['fleet.vehicle.document'].sudo().search(domain, limit=1))

    def _generate_children_for_first_document(self, document):
        if document and hasattr(document, 'generate_missing_periodic_lines_after_approval'):
            document.generate_missing_periodic_lines_after_approval()

    def _create_first_manual_document_from_vehicle(self, document_type):
        self.ensure_one()

        mapping = {
            'assurance': {
                'name': self.assurance_first_name,
                'date_start': self.assurance_first_date_start,
                'date_end': self.assurance_first_date_end,
                'state': self.assurance_first_state,
            },
            'vignette': {
                'name': self.vignette_first_name,
                'date_start': self.vignette_first_date_start,
                'date_end': self.vignette_first_date_end,
                'state': self.vignette_first_state,
            },
            'visite': {
                'name': self.visite_first_name,
                'date_start': self.visite_first_date_start,
                'date_end': self.visite_first_date_end,
                'state': self.visite_first_state,
            },
            'permis_circulation': {
                'name': self.permis_first_name,
                'date_start': self.permis_first_date_start,
                'date_end': self.permis_first_date_end,
                'state': self.permis_first_state,
            },
        }

        data = mapping.get(document_type)
        if not data:
            return False

        if not data.get('date_start'):
            return False

        name = data.get('name') or self._get_first_document_default_name(document_type)

        existing = self.env['fleet.vehicle.document'].sudo().search([
            ('vehicle_id', '=', self.id),
            ('document_type', '=', document_type),
            ('auto_generated', '=', False),
        ], limit=1)

        vals = {
            'name': name,
            'vehicle_id': self.id,
            'document_type': document_type,
            'supplier_id': self.dealer_id.id if self.dealer_id else False,
            'date_start': data['date_start'],
            'date_end': data.get('date_end'),
            'state': data.get('state') or 'not_paid',
            'amount': 0.0,
            'auto_generated': False,
        }

        if existing:
            existing.with_context(skip_document_state_sync=True).write(vals)
            document = existing
        else:
            document = self.env['fleet.vehicle.document'].sudo().create(vals)

        self._generate_children_for_first_document(document)

        return document

    def _create_all_first_manual_documents_from_vehicle(self):
        for rec in self:
            for document_type in ('assurance', 'vignette', 'visite', 'permis_circulation'):
                rec._create_first_manual_document_from_vehicle(document_type)

    def _create_or_update_auto_document(self, document_type):
        self.ensure_one()

        Document = self.env['fleet.vehicle.document'].sudo()

        name = self._get_first_document_default_name(document_type)
        start_date = self.date_mise_circulation or self.purchase_date or fields.Date.context_today(self)

        existing = Document.search([
            ('vehicle_id', '=', self.id),
            ('document_type', '=', document_type),
            ('auto_generated', '=', True),
        ], limit=1)

        vals = {
            'name': name,
            'vehicle_id': self.id,
            'document_type': document_type,
            'supplier_id': self.dealer_id.id if self.dealer_id else False,
            'date_start': start_date,
            'date_end': False,
            'amount': 0.0,
            'auto_generated': True,
        }

        if document_type == 'carte_grise':
            vals['state'] = False
        else:
            vals['state'] = 'not_paid'

        if existing:
            existing.with_context(skip_document_state_sync=True).write(vals)
            return existing

        return Document.create(vals)

    def _create_or_update_registration_and_permit(self):
        for rec in self:
            rec._create_or_update_auto_document('carte_grise')
            rec._create_or_update_auto_document('permis_circulation')
            rec._create_or_update_technical_visits_plan()
    def _create_or_update_technical_visits_plan(self):
        for rec in self:
            if not rec.date_mise_circulation:
                continue

            # 🔥 éviter recréation multiple
            if rec.technical_visit_doc_ids.filtered(lambda d: d.auto_generated):
                continue

            Document = rec.env['fleet.vehicle.document'].sudo()

            start_date = rec.date_mise_circulation + relativedelta(months=6)

            for i in range(9):
                date_start = start_date + relativedelta(months=6 * i)
                date_end = date_start + relativedelta(months=6, days=-1)

                Document.create({
                    'name': f"Visite technique {i+1} - {rec.display_name}",
                    'vehicle_id': rec.id,
                    'document_type': 'visite',
                    'supplier_id': rec.dealer_id.id if rec.dealer_id else False,
                    'date_start': date_start,
                    'date_end': date_end,
                    'amount': 0.0,
                    'state': 'not_paid',
                    'auto_generated': True,
                })

    def _get_documents_plan_base_date(self, bill=False):
        self.ensure_one()
        return (
            self.date_mise_circulation
            or self.purchase_date
            or (bill.invoice_date if bill else False)
            or fields.Date.context_today(self)
        )


    def _generate_paid_vehicle_documents_plan(self, purchase_order=False, bill=False):
        for rec in self:
            rec._create_or_update_registration_and_permit()
            rec._create_all_first_manual_documents_from_vehicle()

            rec.with_context(skip_vehicle_state_update=True).write({
                'documents_generated_on_payment': True
            })

            rec._update_vehicle_state_by_rules()

    def _rename_auto_documents_after_license_plate(self):
        for rec in self:
            if not rec.license_plate or not rec.numero_w:
                continue

            docs = rec.administrative_document_ids.filtered(
                lambda d: d.auto_generated and d.name and rec.numero_w in d.name
            )

            for doc in docs:
                doc.sudo().write({
                    'name': doc.name.replace(rec.numero_w, rec.license_plate)
                })

    def action_generate_first_manual_documents(self):
        for rec in self:
            rec._create_all_first_manual_documents_from_vehicle()
            rec._create_or_update_registration_and_permit()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_confirm_vehicle_info(self):
        for rec in self:
            vin = (rec.vin_sn or '').strip()

            if not rec.numero_w:
                raise ValidationError(_("Le numéro W est obligatoire."))

            if not vin:
                raise ValidationError(_("Le numéro de châssis est obligatoire."))

            if len(vin) != 17:
                raise ValidationError(_("Le numéro de châssis doit contenir exactement 17 caractères."))

            existing_vin = self.search([
                ('id', '!=', rec.id),
                ('vin_sn', '=', vin),
            ], limit=1)

            if existing_vin:
                raise ValidationError(_("Ce numéro de châssis existe déjà."))

            required_values = [
                rec.model_id,
                rec.type_acquisition,
                rec.dealer_id,
                rec.purchase_date,
                rec.date_mise_circulation,
            ]

            if any(not value for value in required_values):
                raise ValidationError(_("Veuillez remplir tous les champs obligatoires avant confirmation."))

            rec._create_or_update_registration_and_permit()
            rec._create_all_first_manual_documents_from_vehicle()
            rec.vehicle_info_confirmed = True
            rec._update_vehicle_state_by_rules()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _has_acquired_contract(self):
        self.ensure_one()

        # ✅ CAS 1 : ACHAT - on garde exactement ta logique actuelle
        contracts = self.purchase_contract_ids.filtered(
            lambda po:
                po.vehicle_purchase_type == 'contract'
                and po.state in ('purchase', 'done')
        )

        for contract in contracts:
            bills = contract._get_related_vendor_bills().filtered(
                lambda m: m.move_type == 'in_invoice' and m.state == 'posted'
            )

            if bills and all(bill.payment_state == 'paid' for bill in bills):
                return True

        # ✅ CAS 2 : LEASING - acquis dès contrat leasing approuvé
        leasing_contracts = self.leasing_contract_ids.filtered(
            lambda po:
                po.vehicle_purchase_type == 'leasing_contract'
                and not po.is_leasing_bill_order
                and po.state != 'cancel'
                and po.leasing_workflow_state == 'approved'
        )

        if leasing_contracts:
            return True

        return False

    def _has_required_paid_documents(self):
        self.ensure_one()

        today = fields.Date.context_today(self)

        def is_paid(doc):
            return (
                doc.state == 'paid'
                or (
                    doc.bill_id
                    and doc.bill_id.move_type == 'in_invoice'
                    and doc.bill_id.state == 'posted'
                    and doc.bill_id.payment_state == 'paid'
                )
            )

        def has_paid_active_doc(doc_type):
            docs = self.administrative_document_ids.filtered(
                lambda d:
                    d.document_type == doc_type
                    and d.date_start
                    and d.date_start <= today
                    and (not d.date_end or d.date_end >= today)
            )

            if not docs:
                return False

            return any(is_paid(doc) for doc in docs)

        def has_unpaid_due_doc(doc_type):
            docs = self.administrative_document_ids.filtered(
                lambda d:
                    d.document_type == doc_type
                    and d.date_start
                    and d.date_start <= today
                    and (not d.date_end or d.date_end >= today)
                    and not is_paid(d)
            )
            return bool(docs)

        # Assurance obligatoire active aujourd'hui
        if not has_paid_active_doc('assurance'):
            return False

        # Vignette obligatoire active aujourd'hui
        if not has_paid_active_doc('vignette'):
            return False

        # Permis circulation obligatoire
        if not has_paid_active_doc('permis_circulation'):
            return False

        # Si facture/document actif non payé => bloque
        for doc_type in ('assurance', 'vignette'):
            if has_unpaid_due_doc(doc_type):
                return False

        # Visite technique obligatoire après 6 mois de mise en circulation
        if self.date_mise_circulation:
            visite_due_date = self.date_mise_circulation + relativedelta(months=6)

            if today >= visite_due_date:
                if not has_paid_active_doc('visite'):
                    return False

                if has_unpaid_due_doc('visite'):
                    return False

        return True
    def _get_state_by_name(self, name):
        return self.env['fleet.vehicle.state'].sudo().with_context(active_test=False).search([
            ('name', '=', name)
        ], limit=1)

    @api.model
    def _reset_vehicle_states(self):
        State = self.env['fleet.vehicle.state'].sudo()
        Vehicle = self.env['fleet.vehicle'].sudo()

        unwanted_names = [
            'New Request',
            'Nouvelle demande',
            'To Order',
            'À commander',
            'Registered',
            'Inscrit',
            'Downgraded',
            'Déclassé',
        ]

        wanted_states = [
            ('En création', 1),
            ('Acquis', 2),
            ('Disponible', 3),
            ('En location', 4),
            ('En réparation', 5),
            ('En réservation', 6),
            ('Bloqué', 7),
            ('Cession', 8),
        ]

        creation_state = False

        for name, sequence in wanted_states:
            state = State.search([('name', '=', name)], limit=1)
            if state:
                state.write({'sequence': sequence})
            else:
                state = State.create({
                    'name': name,
                    'sequence': sequence,
                })

            if name == 'En création':
                creation_state = state

        unwanted_states = State.search([('name', 'in', unwanted_names)])

        if unwanted_states and creation_state:
            Vehicle.search([('state_id', 'in', unwanted_states.ids)]).with_context(
                skip_reset_vehicle_states=True,
                skip_vehicle_state_update=True,
                skip_vehicle_creation_check=True,
            ).write({
                'state_id': creation_state.id
            })
            unwanted_states.unlink()
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        creation_state = self._get_state_by_name('En création')

        if creation_state and 'state_id' in self._fields:
            res['state_id'] = creation_state.id

        return res

    def _has_active_contract(self):
        self.ensure_one()

        today = fields.Date.context_today(self)

        rental_contract = self.env['car.rental.contract'].sudo().search([
            ('state', '=', 'lance'),
            ('rent_start_date', '<=', today),
            '|',
            ('rent_end_date', '=', False),
            ('rent_end_date', '>=', today),
            '|',
            ('current_vehicle_id', '=', self.id),
            ('contract_vehicle_ids.vehicle_id', '=', self.id),
        ], limit=1)

        return bool(rental_contract)

    def _has_open_repair(self):
        self.ensure_one()

        service_logs = self.env['fleet.vehicle.log.services'].sudo().search([
            ('vehicle_id', '=', self.id),
            ('service_type_id.service_code', '=', 'maintenance')
        ])

        return any(log.state not in ('done', 'cancel') for log in service_logs)

    def _has_active_reservation(self):
        self.ensure_one()

        SaleOrder = self.env['sale.order']
        reservation_domain = [('vehicle_id', '=', self.id)]

        if 'is_reservation' in SaleOrder._fields:
            if SaleOrder.search(reservation_domain + [
                ('is_reservation', '=', True),
                ('state', 'in', ['sale', 'done'])
            ]):
                return True

        if 'reservation_state' in SaleOrder._fields:
            if SaleOrder.search(reservation_domain + [
                ('reservation_state', 'in', ['confirmed', 'confirm', 'active'])
            ]):
                return True

        return False

    def _has_paid_purchase_contract(self):
        self.ensure_one()

        contracts = self.purchase_contract_ids.filtered(
            lambda po: po.vehicle_purchase_type == 'contract' and po.state != 'cancel'
        )

        if not contracts:
            return False

        for contract in contracts:
            bills = contract._get_related_vendor_bills().filtered(
                lambda m: m.move_type == 'in_invoice' and m.state == 'posted'
            )

            if bills and all(bill.payment_state == 'paid' for bill in bills):
                return True

        return False

    def _has_all_leasing_echeances_paid(self):
        self.ensure_one()

        contracts = self.leasing_contract_ids.filtered(
            lambda po:
            po.vehicle_purchase_type == 'leasing_contract'
            and not po.is_leasing_bill_order
            and po.state != 'cancel'
            and po.leasing_workflow_state == 'approved'
        )

        if not contracts:
            return False

        for contract in contracts:
            echeances = contract.leasing_echeance_ids
            if echeances and all(e.state == 'paid' for e in echeances):
                return True

        return False

    def _check_vehicle_can_be_blocked(self):
        self.ensure_one()

        if not self.state_id or self.state_id.name != 'Disponible':
            raise ValidationError(_("Seuls les véhicules disponibles peuvent être bloqués."))

        if self.type_acquisition == 'achat' and not self._has_paid_purchase_contract():
            raise ValidationError(_("Impossible de bloquer ce véhicule : le contrat d'achat n'est pas encore totalement payé."))

        if self.type_acquisition == 'leasing' and not self._has_all_leasing_echeances_paid():
            raise ValidationError(_("Impossible de bloquer ce véhicule : toutes les échéances leasing doivent être payées."))

    def _is_cession_ready(self):
        self.ensure_one()

        for sale in self.sale_order_ids.filtered(lambda s: s.state in ('sale', 'done')):
            customer_invoices = sale.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
            )

            if customer_invoices and all(inv.payment_state == 'paid' for inv in customer_invoices):
                return True

        return False

    def _is_auto_block_due(self):
        self.ensure_one()

        if not self.date_mise_circulation:
            return False

        today = fields.Date.context_today(self)
        blocking_date = self.date_mise_circulation + relativedelta(months=61)
        return today >= blocking_date

    def _update_vehicle_state_by_rules(self):
        if self.env.context.get('skip_vehicle_state_update'):
            return

        state_creation = self._get_state_by_name('En création')
        state_acquired = self._get_state_by_name('Acquis')
        state_available = self._get_state_by_name('Disponible')
        state_location = self._get_state_by_name('En location')
        state_repair = self._get_state_by_name('En réparation')
        state_reservation = self._get_state_by_name('En réservation')
        state_blocked = self._get_state_by_name('Bloqué')
        state_cession = self._get_state_by_name('Cession')

        RentalContract = self.env['car.rental.contract'].sudo()

        for rec in self:
            target_state = False

            active_rental_contract = RentalContract.search([
                ('state', '=', 'lance'),
                '|',
                ('current_vehicle_id', '=', rec.id),
                ('contract_vehicle_ids.vehicle_id', '=', rec.id),
            ], limit=1)

            if rec._is_cession_ready() and state_cession:
                target_state = state_cession

            elif (rec.is_blocked_manual or rec._is_auto_block_due()) and state_blocked:
                target_state = state_blocked

            elif rec._has_open_repair() and state_repair:
                target_state = state_repair

            elif active_rental_contract and state_location:
                target_state = state_location

            elif rec._has_active_reservation() and state_reservation:
                target_state = state_reservation

            elif rec._has_active_contract() and state_location:
                target_state = state_location

            elif rec._has_acquired_contract() and rec._has_required_paid_documents() and state_available:
                target_state = state_available

            elif rec._has_acquired_contract() and state_acquired:
                target_state = state_acquired

            elif state_creation:
                target_state = state_creation

            if target_state and rec.state_id != target_state:
                rec.with_context(skip_vehicle_state_update=True).write({
                    'state_id': target_state.id
                })

    def action_block_vehicle(self):
        blocked_state = self._get_state_by_name('Bloqué')

        if not blocked_state:
            raise ValidationError(_("L'état 'Bloqué' n'existe pas."))

        for rec in self:
            rec._check_vehicle_can_be_blocked()
            rec.with_context(skip_vehicle_state_update=True).write({
                'is_blocked_manual': True,
                'state_id': blocked_state.id,
            })

        return True

    def action_unblock_vehicle(self):
        for rec in self:
            if not rec.state_id or rec.state_id.name != 'Bloqué':
                raise ValidationError(_("Seuls les véhicules bloqués peuvent être débloqués."))

            rec.with_context(skip_vehicle_state_update=True).write({
                'is_blocked_manual': False,
            })

        self._update_vehicle_state_by_rules()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('skip_reset_vehicle_states'):
            self._reset_vehicle_states()

        creation_state = self._get_state_by_name('En création')
        new_vals_list = []

        for vals in vals_list:
            vals = dict(vals)

            if creation_state and not vals.get('state_id'):
                vals['state_id'] = creation_state.id

            if 'is_blocked_manual' not in vals:
                vals['is_blocked_manual'] = False

            new_vals_list.append(vals)

        records = super().create(new_vals_list)

        for rec in records:
            if not rec.product_id:
                rec._create_linked_product()

        return records

    def write(self, vals):
        if not self.env.context.get('skip_reset_vehicle_states'):
            self._reset_vehicle_states()

        technical_context = (
            self.env.context.get('skip_vehicle_product_sync')
            or self.env.context.get('skip_vehicle_state_update')
            or self.env.context.get('skip_product_bidirectional_sync')
            or self.env.context.get('skip_vehicle_creation_check')
            or self.env.context.get('from_rental_contract')
        )

        if not technical_context:
            for rec in self:
                if rec.state_id and rec.state_id.name != 'En création':
                    allowed_after_creation = set(vals.keys()).issubset({
                        'license_plate',
                        'state_id',
                        'documents_generated_on_payment',
                        'vehicle_info_confirmed',
                        'is_blocked_manual',
                        'rental_check_availability',
                        'message_follower_ids',
                        'message_ids',
                        'activity_ids',

                        # 🔥 AJOUTER CEUX-CI
                        'assurance_first_name',
                        'assurance_first_date_start',
                        'assurance_first_date_end',
                        'assurance_first_state',

                        'vignette_first_name',
                        'vignette_first_date_start',
                        'vignette_first_date_end',
                        'vignette_first_state',
                    })

                    if not allowed_after_creation:
                        raise ValidationError(
                            _("Modification interdite : seul un véhicule en création est modifiable.")
                        )

        result = super().write(vals)

        if 'license_plate' in vals and vals.get('license_plate'):
            self._rename_auto_documents_after_license_plate()

        if not technical_context:
            for rec in self:
                rec._sync_linked_product()

            self._update_vehicle_state_by_rules()

        return result

    def unlink(self):
        if self.env.context.get('skip_vehicle_product_delete'):
            return super().unlink()

        for rec in self:
            if rec.state_id and rec.state_id.name != 'En création':
                raise ValidationError(_("Suppression interdite : seul un véhicule en création peut être supprimé."))

            purchase_count = self.env['purchase.order'].search_count([
                ('vehicle_id', '=', rec.id)
            ])

            if purchase_count:
                raise ValidationError(_("Impossible de supprimer un véhicule lié à des achats."))

        linked_products = self.mapped('product_template_id')
        result = super().unlink()

        if linked_products:
            linked_products.with_context(skip_product_linked_delete=True).unlink()

        return result

    def init(self):
        self._reset_vehicle_states()

    def action_open_purchase_contracts(self):
        self.ensure_one()

        if self.type_acquisition != 'achat':
            raise ValidationError(_("Ce véhicule n’est pas acquis par achat, donc il ne peut pas avoir de contrat d’achat."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrats achat'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [
                ('vehicle_id', '=', self.id),
                ('vehicle_purchase_type', '=', 'contract')
            ],
            'context': {
                'default_vehicle_id': self.id,
                'default_vehicle_purchase_type': 'contract',
            },
            'target': 'current',
        }

    def action_open_leasing_contracts(self):
        self.ensure_one()

        if self.type_acquisition != 'leasing':
            raise ValidationError(_("Ce véhicule n’est pas acquis en leasing, donc il ne peut pas avoir de contrat leasing."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrats leasing'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [
                ('vehicle_id', '=', self.id),
                ('vehicle_purchase_type', '=', 'leasing_contract'),
                ('is_leasing_bill_order', '=', False),
                ('source_leasing_contract_id', '=', False),
                ('source_leasing_echeance_id', '=', False),
            ],
            'context': {
                'default_vehicle_id': self.id,
                'default_vehicle_purchase_type': 'leasing_contract',
            },
            'target': 'current',
        }

    def action_open_vehicle_expenses(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Dépenses véhicule',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'active_vehicle_id': self.id},
            'target': 'current',
        }

    def action_open_penalite_expenses(self):
        self.ensure_one()

        expense_orders = self.env['purchase.order'].search([
            ('vehicle_purchase_type', '=', 'expense'),
            ('fleet_purchase_service_code', '=', 'penalite'),
            ('penalite_vehicle_line_ids.vehicle_id', '=', self.id),
        ])

        return {
            'type': 'ir.actions.act_window',
            'name': _('Pénalités'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', expense_orders.ids)],
            'target': 'current',
        }

    def action_open_sale_orders(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrats vente'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {
                'default_vehicle_id': self.id,
                'allow_vehicle_sale_edit': True,
                'default_order_line': [(0, 0, {
                    'product_id': self.product_id.id,
                    'name': self.display_name,
                    'product_uom_qty': 1,
                    'price_unit': self.amount_ttc or self.amount_ht or 0.0,
                })] if self.product_id else [],
            },
            'target': 'current',
        }

    def action_open_linked_product(self):
        self.ensure_one()

        if not self.product_id:
            self._create_linked_product()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Produit lié'),
            'res_model': 'product.template',
            'res_id': self.product_id.product_tmpl_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_admin_docs(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents administratifs'),
            'res_model': 'fleet.vehicle.document',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {
                'default_vehicle_id': self.id,
                'search_default_group_by_document_type': 1,
            },
            'target': 'current',
        }

    def action_open_equipments(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Équipements véhicule'),
            'res_model': 'fleet.vehicle.equipment',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
            'target': 'current',
        }