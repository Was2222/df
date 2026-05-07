from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    _sql_constraints = [
        (
            'partner_ref_unique_company',
            'unique(company_id, partner_ref)',
            'La référence fournisseur doit être unique par société.'
        ),
    ]

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule"
    )
    license_plate = fields.Char(
        string="Immatriculation",
        related='vehicle_id.license_plate',
        store=True,
        readonly=True
    )

    numero_w = fields.Char(
        string="Numéro W",
        related='vehicle_id.numero_w',
        store=True,
        readonly=True
    )

    model_name = fields.Char(
        string="Modèle",
        related='vehicle_id.model_name',
        store=True,
        readonly=True
    )

    brand_name = fields.Char(
        string="Marque",
        related='vehicle_id.brand_name',
        store=True,
        readonly=True
    )
    origin = fields.Char(string="Contrat")
    leasing_contract_status = fields.Selection([
        ('a_confirmer', 'À confirmer'),
        ('a_approuver', 'À approuver'),
        ('en_cours', 'En cours'),
        ('fini', 'Fini'),
    ], string="Statut contrat", default='a_confirmer', copy=False)
    vehicle_purchase_type = fields.Selection([
        ('contract', 'Contrat d\'achat véhicule'),
        ('leasing_contract', 'Contrat leasing véhicule'),
        ('expense', 'Dépense / document véhicule'),
    ], string="Type achat véhicule", readonly=True, copy=False)
    service_document_year = fields.Integer(
            string="Année",
            default=lambda self: fields.Date.context_today(self).year
    )
    leasing_workflow_state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Contrat confirmé'),
        ('approved', 'Contrat approuvé'),
        ('cancel', 'Annulé'),
    ], string="Statut leasing", default='draft', copy=False, tracking=True)

    fleet_purchase_service_code = fields.Selection([
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
    ], string="Type document / service", readonly=True, copy=False)

    fleet_document_id = fields.Many2one(
        'fleet.vehicle.document',
        string="Document administratif lié",
        readonly=True,
        copy=False
    )

    fleet_service_code = fields.Selection([
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
        ('equipement', 'Équipement'),
    ], string="Code service flotte", compute="_compute_fleet_service_code", store=True)

    allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_product_ids',
        string="Produits autorisés"
    )

    vendor_bill_count = fields.Integer(
        string="Nombre factures fournisseur",
        compute="_compute_vendor_bill_count"
    )

    has_vendor_bill = fields.Boolean(
        string="A une facture fournisseur",
        compute="_compute_vendor_bill_count"
    )
    observation = fields.Text(string="Observation")
    leasing_contract_number = fields.Char(string="Numéro du contrat")
    leasing_contract_date = fields.Date(string="Date du contrat")
    leasing_first_debit_date = fields.Date(string="Date du 1er prélèvement")
    leasing_end_debit_date = fields.Date(string="Date fin prélèvement")
    leasing_reception_date = fields.Date(string="Date de réception")
    leasing_date_start = fields.Date(string="Date début")
    leasing_date_end = fields.Date(string="Date fin")
    leasing_contract_end_date = fields.Date(string="Date fin du contrat")

    dealer_id = fields.Many2one('res.partner', string="Concessionnaire")
    leasing_company_id = fields.Many2one('res.partner', string="Société de leasing")

    leasing_duration = fields.Integer(string="Durée")
    leasing_months = fields.Integer(string="Mois")
    leasing_deferment_duration = fields.Integer(string="Durée de report")
    leasing_amendment = fields.Char(string="Avenant")
    leasing_comment = fields.Text(string="Commentaire")

    leasing_tax_ids = fields.Many2many(
        'account.tax',
        'purchase_order_leasing_tax_rel',
        'order_id',
        'tax_id',
        string="Taxes leasing",
        domain="[('type_tax_use', 'in', ['purchase', 'none'])]"
    )

    leasing_amount_contract_ht = fields.Float(string="Montant contrat HT")
    leasing_tva = fields.Float(string="TVA")
    leasing_amount_contract_ttc = fields.Float(
        string="Montant contrat TTC",
        compute="_compute_leasing_amounts",
        store=True
    )

    leasing_amount_debit_ttc = fields.Float(string="Montant prélèvement TTC")

    leasing_amount_debit_ht = fields.Float(
        string="Montant prélèvement HT",
        compute="_compute_leasing_debit_amounts",
        store=True
    )

    leasing_debit_tax_amount = fields.Float(
        string="Montant TVA prélèvement",
        compute="_compute_leasing_debit_amounts",
        store=True
    )

    leasing_amount_financed_ht = fields.Float(string="Montant financé HT")
    leasing_amount_financed_ttc = fields.Float(
        string="Montant financé TTC",
        compute="_compute_leasing_amounts",
        store=True
    )
    contract_bank_id = fields.Many2one(
        'res.bank',
        string="Banque"
    )
    payment_journal_id = fields.Many2one(
        'account.journal',
        string="Banque de paiement",
        domain="[('type', '=', 'bank')]"
    )
    contract_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string="Numéro de compte"
    )
    leasing_residual_value_ht = fields.Float(string="Valeur résiduelle HT")
    leasing_residual_value_ttc = fields.Float(
        string="Valeur résiduelle TTC",
        compute="_compute_leasing_amounts",
        store=True
    )

    assurance_attestation_number = fields.Char(string="N° attestation")
    assurance_policy_number = fields.Char(string="Numéro police")
    assurance_type = fields.Char(string="Type assurance")
    assurance_amount = fields.Float(
        string="Montant global assurance",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    assurance_stamp_fee = fields.Float(string="Frais timbre")
    assurance_contract_fee = fields.Float(string="Frais contrat")
    assurance_date_start = fields.Date(string="Date début")
    assurance_date_end = fields.Date(string="Date fin")
    assurance_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    assurance_attachment = fields.Binary(string="Attachement")
    assurance_attachment_filename = fields.Char(string="Nom fichier assurance")

    vignette_number = fields.Char(string="Numéro")
    vignette_amount = fields.Float(
        string="Montant global vignette",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    vignette_date_start = fields.Date(string="Date début")
    vignette_date_end = fields.Date(string="Date fin")
    vignette_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    vignette_attachment = fields.Binary(string="Attachement")
    vignette_attachment_filename = fields.Char(string="Nom fichier vignette")

    visite_number = fields.Char(string="Numéro")
    visite_type = fields.Char(string="Type visite technique")
    visite_center = fields.Char(string="Centre de visite technique")
    visite_amount = fields.Float(
        string="Montant global visite technique",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    visite_date_start = fields.Date(string="Date début")
    visite_date_end = fields.Date(string="Date fin")
    visite_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    visite_attachment = fields.Binary(string="Attachement")
    visite_attachment_filename = fields.Char(string="Nom fichier visite")

    jawaz_number = fields.Char(string="Numéro carte Jawaz")
    jawaz_provider = fields.Char(string="Prestataire Jawaz")
    jawaz_amount = fields.Float(
        string="Montant global Jawaz",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    jawaz_date_start = fields.Date(string="Date début")
    jawaz_date_end = fields.Date(string="Date fin")
    jawaz_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    jawaz_attachment = fields.Binary(string="Pièce jointe Jawaz")
    jawaz_attachment_filename = fields.Char(string="Nom fichier Jawaz")

    carburant_card_number = fields.Char(string="Numéro carte carburant")
    carburant_provider = fields.Char(string="Prestataire carburant")
    carburant_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('essence', 'Essence'),
        ('mixte', 'Mixte'),
    ], string="Type carburant")
    carburant_amount = fields.Float(
        string="Montant global carburant",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    carburant_date_start = fields.Date(string="Date début")
    carburant_date_end = fields.Date(string="Date fin")
    carburant_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    carburant_attachment = fields.Binary(string="Pièce jointe carburant")
    carburant_attachment_filename = fields.Char(string="Nom fichier carburant")

    carte_verte_number = fields.Char(string="Numéro carte verte")
    carte_verte_provider = fields.Char(string="Prestataire")
    carte_verte_amount = fields.Float(
        string="Montant global carte verte",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    carte_verte_date_start = fields.Date(string="Date début")
    carte_verte_date_end = fields.Date(string="Date fin")
    carte_verte_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    carte_verte_attachment = fields.Binary(string="Pièce jointe carte verte")
    carte_verte_attachment_filename = fields.Char(string="Nom fichier carte verte")

    immatriculation_amount = fields.Float(
        string="Montant global frais immatriculation",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    permis_circulation_amount = fields.Float(
        string="Montant global permis de circulation",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )

    carte_grise_amount = fields.Float(
        string="Montant global carte grise",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    penalite_reference = fields.Char(string="Référence pénalité")
    penalite_reason = fields.Char(string="Motif pénalité")
    penalite_amount = fields.Float(
        string="Montant global pénalités",
        compute="_compute_expense_totals",
        store=True,
        readonly=True
    )
    penalite_date = fields.Date(string="Date pénalité")
    penalite_user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )
    penalite_attachment = fields.Binary(string="Pièce jointe pénalité")
    penalite_attachment_filename = fields.Char(string="Nom fichier pénalité")

    assurance_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules assurance",
        domain=[('service_code', '=', 'assurance')]
    )
    vignette_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules vignette",
        domain=[('service_code', '=', 'vignette')]
    )
    visite_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules visite technique",
        domain=[('service_code', '=', 'visite_technique')]
    )
    jawaz_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules Jawaz",
        domain=[('service_code', '=', 'jawaz')]
    )
    carburant_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules carburant",
        domain=[('service_code', '=', 'carburant')]
    )
    carte_verte_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules carte verte",
        domain=[('service_code', '=', 'carte_verte')]
    )
    immatriculation_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules immatriculation",
        domain=[('service_code', '=', 'immatriculation')]
    )
    penalite_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules pénalités",
        domain=[('service_code', '=', 'penalite')]
    )
    permis_circulation_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules permis de circulation",
        domain=[('service_code', '=', 'permis_circulation')]
    )

    carte_grise_vehicle_line_ids = fields.One2many(
        'purchase.order.service.vehicle',
        'purchase_order_id',
        string="Véhicules carte grise",
        domain=[('service_code', '=', 'carte_grise')]
    )
    assurance_vehicle_count = fields.Integer(
        string="Nombre véhicules assurance",
        compute="_compute_service_vehicle_counts"
    )
    jawaz_vehicle_count = fields.Integer(
        string="Nombre véhicules Jawaz",
        compute="_compute_service_vehicle_counts"
    )
    carburant_vehicle_count = fields.Integer(
        string="Nombre véhicules carburant",
        compute="_compute_service_vehicle_counts"
    )
    carte_verte_vehicle_count = fields.Integer(
        string="Nombre véhicules carte verte",
        compute="_compute_service_vehicle_counts"
    )
    immatriculation_vehicle_count = fields.Integer(
        string="Nombre véhicules immatriculation",
        compute="_compute_service_vehicle_counts"
    )
    penalite_vehicle_count = fields.Integer(
        string="Nombre véhicules pénalités",
        compute="_compute_service_vehicle_counts"
    )

    vehicle_expense_amount = fields.Float(
        string="Montant HT véhicule",
        compute="_compute_vehicle_expense_amounts",
        store=False,
        readonly=True
    )

    vehicle_expense_tax = fields.Float(
        string="Taxe véhicule",
        compute="_compute_vehicle_expense_amounts",
        store=False,
        readonly=True
    )

    vehicle_expense_ttc = fields.Float(
        string="Montant TTC véhicule",
        compute="_compute_vehicle_expense_amounts",
        store=False,
        readonly=True
    )

    is_leasing_bill_order = fields.Boolean(
        string="BL issu d'une échéance leasing",
        copy=False,
        readonly=True
    )

    source_leasing_contract_id = fields.Many2one(
        'purchase.order',
        string="Contrat leasing source",
        copy=False,
        readonly=True
    )

    source_leasing_echeance_id = fields.Many2one(
        'leasing.echeance',
        string="Échéance leasing source",
        copy=False,
        readonly=True
    )
    date_approve_display = fields.Char(
        string="Date de confirmation",
        compute="_compute_display_dates",
        store=False
    )
    date_planned_display = fields.Char(
        string="Arrivée prévue",
        compute="_compute_display_dates",
        store=False
    )

    leasing_contract_date_display = fields.Char(
        string="Date du contrat",
        compute="_compute_display_dates",
        store=False
    )
    leasing_first_debit_date_display = fields.Char(
        string="Date du 1er prélèvement",
        compute="_compute_display_dates",
        store=False
    )
    leasing_end_debit_date_display = fields.Char(
        string="Date fin prélèvement",
        compute="_compute_display_dates",
        store=False
    )

    assurance_date_start_display = fields.Char(
        string="Date début assurance",
        compute="_compute_display_dates",
        store=False
    )
    paid_vendor_bill_ref = fields.Char(
        string="Référence facture payée",
        compute="_compute_paid_vendor_bill_info",
        store=False
    )

    paid_vendor_bill_number = fields.Char(
        string="Numéro facture payée",
        compute="_compute_paid_vendor_bill_info",
        store=False
    )
    assurance_date_end_display = fields.Char(
        string="Date fin assurance",
        compute="_compute_display_dates",
        store=False
    )

    vignette_date_start_display = fields.Char(
        string="Date début vignette",
        compute="_compute_display_dates",
        store=False
    )
    vignette_date_end_display = fields.Char(
        string="Date fin vignette",
        compute="_compute_display_dates",
        store=False
    )

    visite_date_start_display = fields.Char(
        string="Date début visite",
        compute="_compute_display_dates",
        store=False
    )
    visite_date_end_display = fields.Char(
        string="Date fin visite",
        compute="_compute_display_dates",
        store=False
    )

    jawaz_date_start_display = fields.Char(
        string="Date début Jawaz",
        compute="_compute_display_dates",
        store=False
    )
    jawaz_date_end_display = fields.Char(
        string="Date fin Jawaz",
        compute="_compute_display_dates",
        store=False
    )

    carburant_date_start_display = fields.Char(
        string="Date début carburant",
        compute="_compute_display_dates",
        store=False
    )
    carburant_date_end_display = fields.Char(
        string="Date fin carburant",
        compute="_compute_display_dates",
        store=False
    )

    carte_verte_date_start_display = fields.Char(
        string="Date début carte verte",
        compute="_compute_display_dates",
        store=False
    )
    carte_verte_date_end_display = fields.Char(
        string="Date fin carte verte",
        compute="_compute_display_dates",
        store=False
    )

    penalite_date_display = fields.Char(
        string="Date pénalité",
        compute="_compute_display_dates",
        store=False
    )
    leasing_amortization_attachment = fields.Binary(string="Tableau amortissement")
    leasing_amortization_attachment_filename = fields.Char(string="Nom fichier tableau amortissement")
    rental_card_type = fields.Selection([
        ('jawaz', 'Jawaz'),
        ('fuel', 'Carburant'),
    ], string="Type carte", compute="_compute_rental_card_type", store=False)

    rental_card_id = fields.Many2one(
        'rental.card',
        string="Carte liée",
        copy=False
    )

    equipment_id = fields.Many2one(
        'fleet.vehicle.equipment',
        string="Équipement lié",
        copy=False
    )
    card_amount_ht = fields.Float(string="Montant HT")

    card_tax_ids = fields.Many2many(
        'account.tax',
        'purchase_order_card_tax_rel',
        'order_id',
        'tax_id',
        string="TVA",
        domain="[('type_tax_use', 'in', ['purchase', 'none'])]"
    )

    card_tax_amount = fields.Float(
        string="Taxe",
        compute="_compute_card_amounts",
        store=True
    )

    card_amount_ttc = fields.Float(
        string="Montant TTC",
        compute="_compute_card_amounts",
        store=True
    )

    # ── Champs related pour affichage infos carte dans la vue ──
    card_linked_number = fields.Char(
        string="N° de carte",
        related='rental_card_id.card_number',
        readonly=True,
        store=False,
    )
    card_linked_type = fields.Selection(
        related='rental_card_id.card_type',
        string="Type de carte",
        readonly=True,
        store=False,
    )
    card_linked_amount = fields.Float(
        string="Solde actuel (DH)",
        related='rental_card_id.amount',
        readonly=True,
        store=False,
    )
    card_linked_date = fields.Date(
        string="Date début carte",
        related='rental_card_id.start_date',
        readonly=True,
        store=False,
    )
    card_linked_used = fields.Boolean(
        string="Utilisée en contrat",
        related='rental_card_id.is_currently_used',
        readonly=True,
        store=False,
    )
    card_linked_contract = fields.Many2one(
        'car.rental.contract',
        string="Contrat lié",
        related='rental_card_id.current_contract_id',
        readonly=True,
        store=False,
    )

    @api.onchange('card_amount_ht', 'card_tax_ids')
    def _onchange_card_amount_sync_order_line(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'expense' and rec.fleet_purchase_service_code in ('jawaz', 'carburant'):
                rec._sync_expense_order_line_from_services()
    @api.depends('card_amount_ht', 'card_tax_ids', 'card_tax_ids.amount')
    def _compute_card_amounts(self):
        for rec in self:
            tax_percent = sum(rec.card_tax_ids.mapped('amount'))
            rec.card_tax_amount = (rec.card_amount_ht or 0.0) * tax_percent / 100.0
            rec.card_amount_ttc = (rec.card_amount_ht or 0.0) + rec.card_tax_amount
    @api.depends('fleet_purchase_service_code')
    def _compute_rental_card_type(self):
        for rec in self:
            if rec.fleet_purchase_service_code == 'jawaz':
                rec.rental_card_type = 'jawaz'
            elif rec.fleet_purchase_service_code == 'carburant':
                rec.rental_card_type = 'fuel'
            elif rec.fleet_purchase_service_code == 'carte_verte':
                rec.rental_card_type = 'green_card'
            else:
                rec.rental_card_type = False
    def _get_card_type_from_service_code(self):
        self.ensure_one()
        mapping = {
            'jawaz': 'jawaz',
            'carburant': 'fuel',
            'carte_verte': 'green_card',
        }
        return mapping.get(self.fleet_purchase_service_code)
    def action_set_contract_a_confirmer(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract' and not rec.is_leasing_bill_order:
                rec.leasing_contract_status = 'a_confirmer'


    def action_set_contract_a_approuver(self):
        for rec in self:
            if rec.vehicle_purchase_type != 'leasing_contract' or rec.is_leasing_bill_order:
                continue
            if rec.leasing_contract_status != 'a_confirmer':
                raise ValidationError(_("Seul un contrat en statut 'À confirmer' peut passer à 'À approuver'."))
            rec.leasing_contract_status = 'a_approuver'

    def _prepare_equipment_order_line_vals(self):
        self.ensure_one()

        if not self.equipment_id:
            raise ValidationError(_("Veuillez sélectionner un équipement."))

        if not self.equipment_id.product_tmpl_id:
            self.equipment_id._create_linked_product()

        product = self.equipment_id.product_tmpl_id.product_variant_id

        if not product:
            raise ValidationError(_("Aucun produit lié à cet équipement."))

        return {
            'product_id': product.id,
            'name': self.equipment_id.name,
            'product_qty': 1.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': self.equipment_id.amount or 0.0,
            'date_planned': fields.Datetime.now(),
        }
    def _update_leasing_contract_status_from_echeances(self):
        for rec in self:
            if rec.vehicle_purchase_type != 'leasing_contract' or rec.is_leasing_bill_order:
                continue

            echeances = rec.leasing_echeance_ids
            if not echeances:
                continue

            all_paid = all(e.state == 'paid' for e in echeances)
            if all_paid:
                rec.leasing_contract_status = 'fini'
            elif rec.leasing_workflow_state == 'approved':
                rec.leasing_contract_status = 'en_cours'
    @api.depends(
        'date_approve',
        'date_planned',
        'leasing_contract_date',
        'leasing_first_debit_date',
        'leasing_end_debit_date',
        'assurance_date_start',
        'assurance_date_end',
        'vignette_date_start',
        'vignette_date_end',
        'visite_date_start',
        'visite_date_end',
        'jawaz_date_start',
        'jawaz_date_end',
        'carburant_date_start',
        'carburant_date_end',
        'carte_verte_date_start',
        'carte_verte_date_end',
        'penalite_date',
    )
    def _compute_paid_vendor_bill_info(self):
        for rec in self:
            rec.paid_vendor_bill_ref = False
            rec.paid_vendor_bill_number = False

            bills = rec._get_related_vendor_bills().filtered(
                lambda m: m.move_type == 'in_invoice' and m.payment_state == 'paid'
            )

            bill = bills[:1] if bills else False
            if bill:
                rec.paid_vendor_bill_ref = bill.ref or ''
                rec.paid_vendor_bill_number = bill.name or ''
    def _compute_display_dates(self):
        for rec in self:
            rec.date_approve_display = rec.date_approve.strftime('%d/%m/%Y') if rec.date_approve else ''
            rec.date_planned_display = rec.date_planned.strftime('%d/%m/%Y') if rec.date_planned else ''

            rec.leasing_contract_date_display = rec.leasing_contract_date.strftime('%d/%m/%Y') if rec.leasing_contract_date else ''
            rec.leasing_first_debit_date_display = rec.leasing_first_debit_date.strftime('%d/%m/%Y') if rec.leasing_first_debit_date else ''
            rec.leasing_end_debit_date_display = rec.leasing_end_debit_date.strftime('%d/%m/%Y') if rec.leasing_end_debit_date else ''

            rec.assurance_date_start_display = rec.assurance_date_start.strftime('%d/%m/%Y') if rec.assurance_date_start else ''
            rec.assurance_date_end_display = rec.assurance_date_end.strftime('%d/%m/%Y') if rec.assurance_date_end else ''

            rec.vignette_date_start_display = rec.vignette_date_start.strftime('%d/%m/%Y') if rec.vignette_date_start else ''
            rec.vignette_date_end_display = rec.vignette_date_end.strftime('%d/%m/%Y') if rec.vignette_date_end else ''

            rec.visite_date_start_display = rec.visite_date_start.strftime('%d/%m/%Y') if rec.visite_date_start else ''
            rec.visite_date_end_display = rec.visite_date_end.strftime('%d/%m/%Y') if rec.visite_date_end else ''

            rec.jawaz_date_start_display = rec.jawaz_date_start.strftime('%d/%m/%Y') if rec.jawaz_date_start else ''
            rec.jawaz_date_end_display = rec.jawaz_date_end.strftime('%d/%m/%Y') if rec.jawaz_date_end else ''

            rec.carburant_date_start_display = rec.carburant_date_start.strftime('%d/%m/%Y') if rec.carburant_date_start else ''
            rec.carburant_date_end_display = rec.carburant_date_end.strftime('%d/%m/%Y') if rec.carburant_date_end else ''

            rec.carte_verte_date_start_display = rec.carte_verte_date_start.strftime('%d/%m/%Y') if rec.carte_verte_date_start else ''
            rec.carte_verte_date_end_display = rec.carte_verte_date_end.strftime('%d/%m/%Y') if rec.carte_verte_date_end else ''

            rec.penalite_date_display = rec.penalite_date.strftime('%d/%m/%Y') if rec.penalite_date else ''
    @api.onchange('contract_bank_id', 'partner_id', 'leasing_company_id', 'vehicle_purchase_type')
    def _onchange_contract_bank_account_id_domain(self):
        for rec in self:
            rec.contract_bank_account_id = False

            domain = []
            partner_ids = []

            if rec.vehicle_purchase_type == 'contract':
                if rec.partner_id:
                    partner_ids.append(rec.partner_id.id)

            elif rec.vehicle_purchase_type == 'leasing_contract':
                if rec.leasing_company_id:
                    partner_ids.append(rec.leasing_company_id.id)
                elif rec.partner_id:
                    partner_ids.append(rec.partner_id.id)

            else:
                if rec.partner_id:
                    partner_ids.append(rec.partner_id.id)
                if rec.leasing_company_id:
                    partner_ids.append(rec.leasing_company_id.id)

            if partner_ids:
                domain.append(('partner_id', 'in', list(set(partner_ids))))

            if rec.contract_bank_id:
                domain.append(('bank_id', '=', rec.contract_bank_id.id))

            return {
                'domain': {
                    'contract_bank_account_id': domain
                }
            }
    def _get_forced_observation_by_service(self, service_code):
        mapping = {
            'assurance': 'Assurance',
            'vignette': 'Vignette',
            'visite_technique': 'Visite technique',
            'maintenance': 'Maintenance',
            'jawaz': 'Jawaz',
            'carburant': 'Carburant',
            'carte_verte': 'Carte verte',
            'immatriculation': 'Frais immatriculation',
            'penalite': 'Pénalités',
            'permis_circulation': 'Permis de circulation',
            'carte_grise': 'Carte grise',
        }
        return mapping.get(service_code)

    @api.onchange('contract_bank_account_id')
    def _onchange_contract_bank_account_id_set_bank(self):
        for rec in self:
            if rec.contract_bank_account_id and rec.contract_bank_account_id.bank_id:
                rec.contract_bank_id = rec.contract_bank_account_id.bank_id


    @api.constrains('contract_bank_id', 'contract_bank_account_id')
    def _check_contract_bank_account_bank(self):
        for rec in self:
            if rec.contract_bank_account_id and rec.contract_bank_id:
                if rec.contract_bank_account_id.bank_id != rec.contract_bank_id:
                    raise ValidationError(_("Le numéro de compte sélectionné n'appartient pas à la banque choisie."))
    @api.onchange('contract_bank_account_id')
    def _onchange_contract_bank_account_id_set_bank(self):
        for rec in self:
            if rec.contract_bank_account_id and rec.contract_bank_account_id.bank_id:
                rec.contract_bank_id = rec.contract_bank_account_id.bank_id

    @api.constrains('contract_bank_id', 'contract_bank_account_id')
    def _check_contract_bank_account_bank(self):
        for rec in self:
            if rec.contract_bank_account_id and rec.contract_bank_id:
                if rec.contract_bank_account_id.bank_id != rec.contract_bank_id:
                    raise ValidationError(_("Le numéro de compte sélectionné n'appartient pas à la banque choisie."))
    @api.onchange('service_document_year')
    def _onchange_service_document_year(self):
        for rec in self:
            all_lines = (
                rec.assurance_vehicle_line_ids
                | rec.vignette_vehicle_line_ids
                | rec.visite_vehicle_line_ids
                | rec.jawaz_vehicle_line_ids
                | rec.carburant_vehicle_line_ids
                | rec.carte_verte_vehicle_line_ids
                | rec.immatriculation_vehicle_line_ids
                | rec.penalite_vehicle_line_ids
                | rec.permis_circulation_vehicle_line_ids
                | rec.carte_grise_vehicle_line_ids
            )
            for line in all_lines:
                line.document_id = False
    @api.depends(
        'assurance_vehicle_line_ids',
        'vignette_vehicle_line_ids',
        'visite_vehicle_line_ids',
        'jawaz_vehicle_line_ids',
        'carburant_vehicle_line_ids',
        'carte_verte_vehicle_line_ids',
        'immatriculation_vehicle_line_ids',
        'penalite_vehicle_line_ids',
        'permis_circulation_vehicle_line_ids',
        'carte_grise_vehicle_line_ids'
    )
    def _compute_service_vehicle_counts(self):
        for rec in self:
            rec.assurance_vehicle_count = len(rec.assurance_vehicle_line_ids)
            rec.jawaz_vehicle_count = len(rec.jawaz_vehicle_line_ids)
            rec.carburant_vehicle_count = len(rec.carburant_vehicle_line_ids)
            rec.carte_verte_vehicle_count = len(rec.carte_verte_vehicle_line_ids)
            rec.immatriculation_vehicle_count = len(rec.immatriculation_vehicle_line_ids)
            rec.penalite_vehicle_count = len(rec.penalite_vehicle_line_ids)

    def _sync_vignette_visite_amounts_from_lines(self):
        for rec in self.filtered(lambda r: r.vehicle_purchase_type == 'expense'):
            vals = {}

            if rec.fleet_purchase_service_code == 'vignette':
                total = sum(rec.vignette_vehicle_line_ids.mapped('amount'))
                if rec.vignette_amount != total:
                    vals['vignette_amount'] = total

            if rec.fleet_purchase_service_code == 'visite_technique':
                total = sum(rec.visite_vehicle_line_ids.mapped('amount'))
                if rec.visite_amount != total:
                    vals['visite_amount'] = total

            if vals:
                super(PurchaseOrder, rec.with_context(skip_vehicle_reapply=True)).write(vals)

    def _get_related_fleet_documents(self):
        self.ensure_one()

        documents = self.env['fleet.vehicle.document']

        if self.fleet_document_id:
            documents |= self.fleet_document_id

        documents |= self._get_service_vehicle_lines().mapped('document_id')

        return documents.filtered(lambda d: d)
    def action_remove_leasing_amortization_attachment(self):
        for rec in self:
            paid_echeances = rec.leasing_echeance_ids.filtered(
                lambda e: e.state == 'paid' or (e.amount_paid and e.amount_paid > 0)
            )

            if paid_echeances:
                raise ValidationError(_(
                    "Suppression impossible : au moins une échéance du tableau est déjà payée ou partiellement payée."
                ))

            # supprimer les échéances si aucune n'est payée
            if rec.leasing_echeance_ids:
                rec.leasing_echeance_ids.unlink()

            # supprimer le fichier importé
            rec.write({
                'leasing_amortization_attachment': False,
                'leasing_amortization_attachment_filename': False,
            })

        return True
    def _sync_related_documents_with_purchase(self, bill=False):
        for rec in self.filtered(lambda r: r.vehicle_purchase_type == 'expense'):
            documents = rec._get_related_fleet_documents()
            if not documents:
                continue

            linked_bill = bill
            if linked_bill and linked_bill.move_type != 'in_invoice':
                linked_bill = False

            if not linked_bill:
                linked_bill = rec._get_related_vendor_bills().filtered(lambda m: m.move_type == 'in_invoice')[:1]

            line_amount_by_doc = {}
            for line in rec._get_service_vehicle_lines().filtered(lambda l: l.document_id):
                line_amount_by_doc[line.document_id.id] = line.amount or 0.0

            if rec.fleet_document_id and rec.fleet_document_id.id not in line_amount_by_doc:
                line_amount_by_doc[rec.fleet_document_id.id] = rec._get_service_total_amount()

            for doc in documents:
                vals = {
                    'purchase_order_id': rec.id,
                }

                if linked_bill:
                    vals.update({
                        'bill_id': linked_bill.id,
                        'invoice_number': linked_bill.ref or linked_bill.name or False,
                    })

                if doc.id in line_amount_by_doc and line_amount_by_doc[doc.id] > 0:
                    vals['amount'] = line_amount_by_doc[doc.id]

                doc.with_context(skip_document_state_sync=True).write(vals)

            documents._sync_state_with_bill()

    @api.depends(
        'vehicle_purchase_type',
        'fleet_purchase_service_code',
        'assurance_vehicle_line_ids.amount',
        'vignette_vehicle_line_ids.amount',
        'visite_vehicle_line_ids.amount',
        'jawaz_vehicle_line_ids.amount',
        'carburant_vehicle_line_ids.amount',
        'carte_verte_vehicle_line_ids.amount',
        'immatriculation_vehicle_line_ids.amount',
        'penalite_vehicle_line_ids.amount',
    )
    def _compute_expense_totals(self):
        for rec in self:
            rec.assurance_amount = sum(rec.assurance_vehicle_line_ids.mapped('amount'))
            rec.vignette_amount = sum(rec.vignette_vehicle_line_ids.mapped('amount'))
            rec.visite_amount = sum(rec.visite_vehicle_line_ids.mapped('amount'))
            rec.jawaz_amount = sum(rec.jawaz_vehicle_line_ids.mapped('amount'))
            rec.carburant_amount = sum(rec.carburant_vehicle_line_ids.mapped('amount'))
            rec.carte_verte_amount = sum(rec.carte_verte_vehicle_line_ids.mapped('amount'))
            rec.immatriculation_amount = sum(rec.immatriculation_vehicle_line_ids.mapped('amount'))
            rec.penalite_amount = sum(rec.penalite_vehicle_line_ids.mapped('amount'))
            rec.permis_circulation_amount = sum(rec.permis_circulation_vehicle_line_ids.mapped('amount'))
            rec.carte_grise_amount = sum(rec.carte_grise_vehicle_line_ids.mapped('amount'))

    @api.depends(
        'fleet_purchase_service_code',
        'order_line.tax_ids',
        'order_line.tax_ids.amount',
        'assurance_vehicle_line_ids.amount',
        'assurance_vehicle_line_ids.vehicle_id',
        'vignette_vehicle_line_ids.amount',
        'vignette_vehicle_line_ids.vehicle_id',
        'visite_vehicle_line_ids.amount',
        'visite_vehicle_line_ids.vehicle_id',
        'jawaz_vehicle_line_ids.amount',
        'jawaz_vehicle_line_ids.vehicle_id',
        'carburant_vehicle_line_ids.amount',
        'carburant_vehicle_line_ids.vehicle_id',
        'carte_verte_vehicle_line_ids.amount',
        'carte_verte_vehicle_line_ids.vehicle_id',
        'immatriculation_vehicle_line_ids.amount',
        'immatriculation_vehicle_line_ids.vehicle_id',
        'penalite_vehicle_line_ids.amount',
        'penalite_vehicle_line_ids.vehicle_id',
    )
    def _compute_vehicle_expense_amounts(self):
        for rec in self:
            vehicle_id = rec.env.context.get('active_vehicle_id')

            if not vehicle_id:
                rec.vehicle_expense_amount = 0.0
                rec.vehicle_expense_tax = 0.0
                rec.vehicle_expense_ttc = 0.0
                continue

            total_ht = 0.0
            for line in rec._get_service_vehicle_lines():
                if line.vehicle_id.id == vehicle_id:
                    total_ht += (line.amount or 0.0)

            tax_percent = 0.0
            main_line = rec.order_line.filtered(lambda l: not l.display_type)[:1]
            if main_line and main_line.tax_ids:
                tax_percent = sum(main_line.tax_ids.mapped('amount'))

            tax = total_ht * tax_percent / 100.0
            ttc = total_ht + tax

            rec.vehicle_expense_amount = total_ht
            rec.vehicle_expense_tax = tax
            rec.vehicle_expense_ttc = ttc

    @api.depends(
        'fleet_purchase_service_code',
        'order_line.product_id',
        'order_line.product_id.product_tmpl_id.fleet_service_type_id.service_code'
    )
    def _compute_fleet_service_code(self):
        allowed_codes = (
            'maintenance', 'vignette', 'visite_technique', 'assurance',
            'jawaz', 'carburant', 'carte_verte', 'immatriculation',
            'penalite', 'permis_circulation', 'carte_grise'
        )
        for rec in self:
            code = rec.fleet_purchase_service_code or False
            if not code:
                for line in rec.order_line:
                    product = line.product_id
                    if not product:
                        continue
                    tmpl = product.product_tmpl_id
                    service_type = tmpl.fleet_service_type_id if tmpl else False
                    if service_type and service_type.service_code in allowed_codes:
                        code = service_type.service_code
                        break
            rec.fleet_service_code = code

    @api.depends('vehicle_purchase_type', 'fleet_purchase_service_code', 'vehicle_id')
    def _compute_allowed_product_ids(self):
        Product = self.env['product.product']

        for rec in self:
            products = Product.browse()

            if rec.vehicle_purchase_type in ('contract', 'leasing_contract'):
                if rec.is_leasing_bill_order:
                    products = Product.search([('purchase_ok', '=', True)], limit=1000)
                elif rec.vehicle_id and rec.vehicle_id.product_id:
                    products = rec.vehicle_id.product_id

            elif rec.vehicle_purchase_type == 'expense':
                if rec.fleet_purchase_service_code:
                    products = Product.search([
                        ('purchase_ok', '=', True),
                        ('product_tmpl_id.fleet_service_type_id.service_code', '=', rec.fleet_purchase_service_code)
                    ])
                else:
                    products = Product.search([('purchase_ok', '=', True)])

            else:
                products = Product.search([('purchase_ok', '=', True)])

            rec.allowed_product_ids = products

    @api.depends(
        'vehicle_purchase_type',
        'amount_untaxed',
        'amount_total',
        'leasing_amount_financed_ht',
        'leasing_residual_value_ht',
        'leasing_tva'
    )
    def _compute_leasing_amounts(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract':
                rec.leasing_amount_contract_ht = rec.amount_untaxed or 0.0
                rec.leasing_tva = rec.leasing_tva or 0.0
                rec.leasing_amount_contract_ttc = rec.amount_total or 0.0
            else:
                rec.leasing_amount_contract_ttc = (
                    (rec.leasing_amount_contract_ht or 0.0)
                    + (rec.leasing_tva or 0.0)
                )

            rec.leasing_amount_financed_ttc = (
                (rec.leasing_amount_financed_ht or 0.0)
                + (rec.leasing_tva or 0.0)
            )

            rec.leasing_residual_value_ttc = (
                (rec.leasing_residual_value_ht or 0.0)
                + (rec.leasing_tva or 0.0)
            )

    @api.onchange('order_line', 'vehicle_purchase_type')
    def _onchange_leasing_contract_totals(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract':
                rec.leasing_amount_contract_ht = rec.amount_untaxed or 0.0
                rec.leasing_amount_contract_ttc = rec.amount_total or 0.0

    @api.depends('leasing_amount_debit_ttc', 'leasing_tax_ids', 'leasing_tax_ids.amount')
    def _compute_leasing_debit_amounts(self):
        for rec in self:
            ttc = rec.leasing_amount_debit_ttc or 0.0
            total_tax_percent = sum(rec.leasing_tax_ids.mapped('amount'))

            if total_tax_percent:
                ht = ttc / (1 + (total_tax_percent / 100.0))
                tax_amount = ttc - ht
            else:
                ht = ttc
                tax_amount = 0.0

            rec.leasing_amount_debit_ht = ht
            rec.leasing_debit_tax_amount = tax_amount

    @api.onchange('leasing_amount_debit_ttc', 'leasing_tax_ids')
    def _onchange_leasing_debit_amounts(self):
        for rec in self:
            ttc = rec.leasing_amount_debit_ttc or 0.0
            total_tax_percent = sum(rec.leasing_tax_ids.mapped('amount'))

            if total_tax_percent:
                ht = ttc / (1 + (total_tax_percent / 100.0))
                tax_amount = ttc - ht
            else:
                ht = ttc
                tax_amount = 0.0

            rec.leasing_amount_debit_ht = ht
            rec.leasing_debit_tax_amount = tax_amount

    @api.constrains('vehicle_purchase_type', 'leasing_amount_debit_ttc', 'leasing_tax_ids')
    def _check_leasing_debit_values(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract':
                if rec.leasing_amount_debit_ttc < 0:
                    raise ValidationError(_("Le montant prélèvement TTC ne peut pas être négatif."))
                if rec.leasing_amount_debit_ttc and not rec.leasing_tax_ids:
                    raise ValidationError(_("Veuillez choisir au moins une taxe leasing."))

    @api.depends('invoice_ids')
    def _compute_vendor_bill_count(self):
        for order in self:
            bills = order._get_related_vendor_bills()
            order.vendor_bill_count = len(bills)
            order.has_vendor_bill = bool(bills)

    def _get_related_vendor_bills(self):
        self.ensure_one()

        bills = self.invoice_ids.filtered(lambda m: m.move_type == 'in_invoice')
        if bills:
            return bills

        bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('invoice_line_ids.purchase_line_id.order_id', '=', self.id),
        ])
        if bills:
            return bills

        if self.name:
            bills = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('invoice_origin', 'ilike', self.name),
            ])
            if bills:
                return bills

        return self.env['account.move']

    @api.onchange('fleet_purchase_service_code')
    def _onchange_auto_product(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'expense' and rec.fleet_purchase_service_code:
                product = self.env['product.product'].search([
                    ('purchase_ok', '=', True),
                    ('product_tmpl_id.fleet_service_type_id.service_code', '=', rec.fleet_purchase_service_code)
                ], limit=1)

                if product and not rec.order_line:
                    rec.order_line = [(0, 0, {
                        'product_id': product.id,
                        'name': product.description_purchase or product.display_name,
                        'product_qty': 1.0,
                        'product_uom_id': product.uom_id.id,
                        'price_unit': product.standard_price or 0.0,
                        'date_planned': fields.Datetime.now(),
                    })]

    def _generate_unique_partner_ref(self):
        self.ensure_one()
        if self.partner_ref:
            return self.partner_ref

        prefix = "PO-FLT-%s-" % fields.Date.context_today(self).strftime("%Y%m%d")
        number = 1
        while True:
            candidate = f"{prefix}{number:04d}"
            exists = self.search_count([
                ('id', '!=', self.id),
                ('company_id', '=', self.company_id.id),
                ('partner_ref', '=', candidate),
            ])
            if not exists:
                return candidate
            number += 1

    def action_open_bill_or_purchase(self):
        self.ensure_one()

        bills = self._get_related_vendor_bills()

        if len(bills) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Facture fournisseur'),
                'res_model': 'account.move',
                'res_id': bills.id,
                'view_mode': 'form',
                'target': 'current',
            }

        if len(bills) > 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Factures fournisseur'),
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'domain': [('id', 'in', bills.ids)],
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de commande'),
            'res_model': 'purchase.order',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_vendor_bills_only(self):
        self.ensure_one()

        bills = self._get_related_vendor_bills()
        if not bills:
            raise ValidationError(_("Aucune facture fournisseur n'existe encore pour ce bon de commande."))

        if len(bills) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Facture fournisseur'),
                'res_model': 'account.move',
                'res_id': bills.id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Factures fournisseur'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bills.ids)],
            'target': 'current',
        }

    def _get_forced_purchase_type_from_context(self):
        self.ensure_one()
        return self.env.context.get('default_vehicle_purchase_type')

    def _get_forced_service_code_from_context(self):
        self.ensure_one()
        return self.env.context.get('default_fleet_purchase_service_code')

    def _validate_forced_purchase_configuration(self):
        for rec in self:
            if rec.is_leasing_bill_order:
                continue

            if rec.vehicle_purchase_type == 'contract' and rec.vehicle_id and rec.vehicle_id.type_acquisition != 'achat':
                raise ValidationError(_("Ce menu est réservé aux véhicules acquis par achat."))

            if rec.vehicle_purchase_type == 'leasing_contract' and rec.vehicle_id and rec.vehicle_id.type_acquisition != 'leasing':
                raise ValidationError(_("Ce menu est réservé aux véhicules acquis en leasing."))

    @api.constrains('vehicle_id', 'vehicle_purchase_type', 'is_leasing_bill_order')
    def _check_vehicle_purchase_type(self):
        for rec in self:
            if not rec.vehicle_id or not rec.vehicle_purchase_type:
                continue

            if rec.is_leasing_bill_order:
                continue

            if rec.vehicle_purchase_type == 'contract' and rec.vehicle_id.type_acquisition != 'achat':
                raise ValidationError(_("Un contrat d'achat ne peut être lié qu'à un véhicule acquis en achat."))

            if rec.vehicle_purchase_type == 'leasing_contract' and rec.vehicle_id.type_acquisition != 'leasing':
                raise ValidationError(_("Un contrat leasing ne peut être lié qu'à un véhicule acquis en leasing."))

    @api.constrains('vehicle_id', 'vehicle_purchase_type', 'state', 'is_leasing_bill_order')
    def _check_unique_vehicle_contracts(self):
        for rec in self:
            if not rec.vehicle_id:
                continue

            if rec.vehicle_purchase_type not in ('contract', 'leasing_contract'):
                continue

            if rec.is_leasing_bill_order:
                continue

            existing_orders = self.search([
                ('id', '!=', rec.id),
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('vehicle_purchase_type', '=', rec.vehicle_purchase_type),
                ('state', '!=', 'cancel'),
            ])

            existing_orders = existing_orders.filtered(lambda o: not o.is_leasing_bill_order)

            if existing_orders:
                if rec.vehicle_purchase_type == 'contract':
                    raise ValidationError(_("Ce véhicule a déjà un contrat d'achat."))
                else:
                    raise ValidationError(_("Ce véhicule a déjà un contrat leasing."))

    @api.constrains('vehicle_purchase_type', 'fleet_purchase_service_code')
    def _check_document_type_presence(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'expense' and not rec.fleet_purchase_service_code:
                raise ValidationError(_("Le type documentaire/service est obligatoire pour ce type d'achat."))

    def _prepare_vehicle_order_line_vals(self, vehicle):
        self.ensure_one()

        if not vehicle.product_id and hasattr(vehicle, '_create_linked_product'):
            vehicle._create_linked_product()

        if not vehicle.product_id:
            raise ValidationError(_("Ce véhicule n'a pas de produit lié."))

        product = vehicle.product_id

        if not product.uom_id:
            raise ValidationError(_("Le produit lié au véhicule n'a pas d'unité de mesure."))

        name = product.description_purchase or product.display_name

        return {
            'product_id': product.id,
            'name': name,
            'product_qty': 1.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': vehicle.amount_ht or product.standard_price or 0.0,
            'date_planned': fields.Datetime.now(),
        }

    def _prepare_leasing_bill_order_line_vals(self, echeance):
        self.ensure_one()

        if not self.vehicle_id:
            raise ValidationError(_("Aucun véhicule n'est lié au contrat leasing."))

        product = self.env['product.product'].search([
            ('purchase_ok', '=', True),
            ('name', '=', 'Échéance leasing'),
        ], limit=1)

        if not product:
            raise ValidationError(_(
                "Créez d'abord un produit achat de type service nommé 'Échéance leasing'."
            ))

        if not product.uom_id:
            raise ValidationError(_("Le produit 'Échéance leasing' n'a pas d'unité de mesure."))

        amount_to_bill = echeance.amount_due if echeance.amount_due > 0 else echeance.amount_total

        vehicle_name = (
            self.vehicle_id.display_name
            or self.vehicle_id.license_plate
            or self.vehicle_id.name
            or ''
        )

        return {
            'product_id': product.id,
            'name': _("Prélèvement leasing - %(veh)s - Échéance %(seq)s - %(date)s") % {
                'veh': vehicle_name,
                'seq': echeance.sequence,
                'date': echeance.date_echeance or '',
            },
            'product_qty': 1.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': amount_to_bill,
            'tax_ids': [(6, 0, [])],
            'date_planned': fields.Datetime.now(),
        }

    def _reset_vehicle_contract_line(self):
        self.ensure_one()
        self.order_line = [(5, 0, 0)]

    def _set_vehicle_contract_line(self):
        self.ensure_one()

        if not self.vehicle_id:
            return

        line_vals = self._prepare_vehicle_order_line_vals(self.vehicle_id)
        self.order_line = [(5, 0, 0), (0, 0, line_vals)]

    def _ensure_vehicle_contract_line(self):
        for rec in self:
            if not rec.vehicle_id:
                continue

            if rec.vehicle_purchase_type not in ('contract', 'leasing_contract'):
                continue

            if rec.is_leasing_bill_order:
                continue

            valid_lines = rec.order_line.filtered(lambda l: not l.display_type)
            if valid_lines and all(line.product_id and line.product_uom_id for line in valid_lines):
                continue

            line_vals = rec._prepare_vehicle_order_line_vals(rec.vehicle_id)
            rec.with_context(skip_vehicle_reapply=True).write({
                'order_line': [(5, 0, 0), (0, 0, line_vals)]
            })

    def _get_service_total_amount(self):
        self.ensure_one()

        if self.fleet_purchase_service_code == 'assurance':
            return sum(self.assurance_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'jawaz':
            return sum(self.jawaz_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'carburant':
            return sum(self.carburant_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'carte_verte':
            return sum(self.carte_verte_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'immatriculation':
            return sum(self.immatriculation_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'penalite':
            return sum(self.penalite_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'vignette':
            return self.vignette_amount or 0.0
        if self.fleet_purchase_service_code == 'visite_technique':
            return self.visite_amount or 0.0
        if self.fleet_purchase_service_code == 'permis_circulation':
            return sum(self.permis_circulation_vehicle_line_ids.mapped('amount'))
        if self.fleet_purchase_service_code == 'carte_grise':
            return sum(self.carte_grise_vehicle_line_ids.mapped('amount'))
        return 0.0

    def _get_service_vehicle_lines(self):
        self.ensure_one()

        if self.fleet_purchase_service_code == 'assurance':
            return self.assurance_vehicle_line_ids
        if self.fleet_purchase_service_code == 'vignette':
            return self.vignette_vehicle_line_ids
        if self.fleet_purchase_service_code == 'visite_technique':
            return self.visite_vehicle_line_ids
        if self.fleet_purchase_service_code == 'jawaz':
            return self.jawaz_vehicle_line_ids
        if self.fleet_purchase_service_code == 'carburant':
            return self.carburant_vehicle_line_ids
        if self.fleet_purchase_service_code == 'carte_verte':
            return self.carte_verte_vehicle_line_ids
        if self.fleet_purchase_service_code == 'immatriculation':
            return self.immatriculation_vehicle_line_ids
        if self.fleet_purchase_service_code == 'penalite':
            return self.penalite_vehicle_line_ids
        if self.fleet_purchase_service_code == 'permis_circulation':
            return self.permis_circulation_vehicle_line_ids
        if self.fleet_purchase_service_code == 'carte_grise':
            return self.carte_grise_vehicle_line_ids
        return self.env['purchase.order.service.vehicle']

    def _prepare_expense_order_line_vals(self):
        self.ensure_one()

        service_code = self.fleet_purchase_service_code
        if not service_code:
            return False

        product = self.order_line.filtered(
            lambda l: not l.display_type and l.product_id
        )[:1].product_id

        if not product:
            product = self.env['product.product'].search([
                ('purchase_ok', '=', True),
                ('product_tmpl_id.fleet_service_type_id.service_code', '=', service_code)
            ], limit=1)

        if not product:
            raise ValidationError(_("Aucun produit achat n'est configuré pour ce type de service."))

        if not product.uom_id:
            raise ValidationError(_("Le produit sélectionné n'a pas d'unité de mesure."))

        # =========================================================
        # CARTES
        # =========================================================
        if service_code in ('jawaz', 'carburant'):

            total_ht = self.card_amount_ht or 0.0
            total_ttc = self.card_amount_ttc or total_ht

            taxes = [(6, 0, self.card_tax_ids.ids)]

        # =========================================================
        # SERVICES VEHICULES
        # =========================================================
        else:

            service_lines = self._get_service_vehicle_lines()

            total_ht = sum(service_lines.mapped('amount'))
            total_taxe = sum(service_lines.mapped('tax_amount'))
            total_ttc = sum(service_lines.mapped('amount_ttc'))

            # fallback
            if total_ttc <= 0:
                existing_line = self.order_line.filtered(
                    lambda l: not l.display_type
                )[:1]

                if existing_line:
                    total_ttc = existing_line.price_unit or 0.0

            # 🔥 garder les taxes pour calcul des lignes véhicules
            taxes = [(6, 0, self.order_line[:1].tax_ids.ids)]

        return {
            'product_id': product.id,
            'name': product.description_purchase or product.display_name,
            'product_qty': 1.0,
            'product_uom_id': product.uom_id.id,

            # 🔥 TOTAL TTC DE TOUS LES VEHICULES
            'price_unit': total_ttc,

            'tax_ids': taxes,
            'date_planned': fields.Datetime.now(),
        }

    def _sync_expense_order_line_from_services(self):
        for rec in self:
            if rec.vehicle_purchase_type != 'expense':
                continue

            if rec.fleet_purchase_service_code not in (
                'assurance', 'vignette', 'visite_technique',
                'jawaz', 'carburant', 'carte_verte',
                'immatriculation', 'penalite',
                'permis_circulation', 'carte_grise'
            ):
                continue

            line_vals = rec._prepare_expense_order_line_vals()
            if not line_vals:
                continue

            valid_lines = rec.order_line.filtered(lambda l: not l.display_type)

            if not valid_lines:
                rec.order_line = [(0, 0, line_vals)]
                continue

            main_line = valid_lines[0]
            main_line.write(line_vals)

            extra_lines = valid_lines[1:]
            if extra_lines:
                extra_lines.unlink()
    def action_create_vendor_bill(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract' and not rec.is_leasing_bill_order:
                raise ValidationError(_(
                    "Vous ne pouvez pas créer une facture directement depuis le contrat leasing. "
                    "La facturation doit se faire depuis l'échéancier via le BL."
                ))

        res = self.action_create_invoice()

        tracking = self.env['fleet.location.tracking']

        for order in self.filtered(lambda o: o.vehicle_purchase_type == 'expense'):
            bills = order._get_related_vendor_bills().filtered(lambda m: m.move_type == 'in_invoice')

            linked_bill = bills[:1] if bills else False

            if linked_bill:
                tracking.sync_invoice_info_from_purchase_order(order, linked_bill)
                order._sync_related_documents_with_purchase(bill=linked_bill)

        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        vehicle_id = res.get('vehicle_id') or self.env.context.get('default_vehicle_id')
        vehicle_purchase_type = self.env.context.get('default_vehicle_purchase_type')
        fleet_purchase_service_code = self.env.context.get('default_fleet_purchase_service_code')
        fleet_document_id = self.env.context.get('default_fleet_document_id')
        service_document_year = self.env.context.get('default_service_document_year')

        if vehicle_purchase_type:
            res['vehicle_purchase_type'] = vehicle_purchase_type

        if fleet_purchase_service_code:
            res['fleet_purchase_service_code'] = fleet_purchase_service_code
            res['observation'] = self._get_forced_observation_by_service(fleet_purchase_service_code)

        if fleet_document_id:
            res['fleet_document_id'] = fleet_document_id

        if service_document_year:
            res['service_document_year'] = service_document_year
        elif 'service_document_year' in fields_list:
            res['service_document_year'] = fields.Date.context_today(self).year

        if vehicle_id and vehicle_purchase_type in ('contract', 'leasing_contract'):
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
            if vehicle.exists():
                if not vehicle.product_id and hasattr(vehicle, '_create_linked_product'):
                    vehicle._create_linked_product()

                if vehicle.product_id:
                    product = vehicle.product_id

                    if not product.uom_id:
                        raise ValidationError(_("Le produit lié au véhicule n'a pas d'unité de mesure."))

                    line_vals = {
                        'product_id': product.id,
                        'name': product.description_purchase or product.display_name,
                        'product_qty': 1.0,
                        'product_uom_id': product.uom_id.id,
                        'price_unit': vehicle.amount_ht or product.standard_price or 0.0,
                        'date_planned': fields.Datetime.now(),
                    }
                    res['order_line'] = [(0, 0, line_vals)]

                if vehicle.dealer_id and not res.get('partner_id'):
                    res['partner_id'] = vehicle.dealer_id.id

        target_partner = False

        if vehicle_purchase_type == 'leasing_contract':
            if res.get('leasing_company_id'):
                target_partner = self.env['res.partner'].browse(res['leasing_company_id'])
            elif res.get('partner_id'):
                target_partner = self.env['res.partner'].browse(res['partner_id'])
        elif vehicle_purchase_type == 'contract':
            if res.get('partner_id'):
                target_partner = self.env['res.partner'].browse(res['partner_id'])

        if target_partner:
            bank_accounts = self.env['res.partner.bank'].search([
                ('partner_id', '=', target_partner.id)
            ], limit=2)

            if len(bank_accounts) == 1:
                res['contract_bank_account_id'] = bank_accounts.id
                res['contract_bank_id'] = bank_accounts.bank_id.id

        return res
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_set_purchase_type(self):
        for rec in self:
            forced_type = rec._get_forced_purchase_type_from_context()
            forced_service = rec._get_forced_service_code_from_context()

            if forced_type:
                rec.vehicle_purchase_type = forced_type
            if forced_service:
                rec.fleet_purchase_service_code = forced_service

            if not rec.vehicle_id:
                if rec.vehicle_purchase_type in ('contract', 'leasing_contract') and not rec.is_leasing_bill_order:
                    rec._reset_vehicle_contract_line()
                continue

            if rec.vehicle_purchase_type in ('contract', 'leasing_contract') and not rec.is_leasing_bill_order:
                rec._set_vehicle_contract_line()

            if rec.vehicle_id.dealer_id and not rec.partner_id:
                rec.partner_id = rec.vehicle_id.dealer_id.id

    @api.onchange('order_line')
    def _onchange_order_line_detect_service_code(self):
        allowed_codes = (
            'maintenance', 'vignette', 'visite_technique', 'assurance',
            'jawaz', 'carburant', 'carte_verte', 'immatriculation', 'penalite'
        )
        for rec in self:
            if rec.vehicle_purchase_type != 'expense':
                continue

            forced_service = rec._get_forced_service_code_from_context()
            if forced_service:
                rec.fleet_purchase_service_code = forced_service
                continue

            detected = False
            for line in rec.order_line:
                product = line.product_id
                if not product:
                    continue
                service_type = product.product_tmpl_id.fleet_service_type_id
                if service_type and service_type.service_code in allowed_codes:
                    detected = service_type.service_code
                    break

            if detected:
                rec.fleet_purchase_service_code = detected

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []

        for vals in vals_list:
            vals = dict(vals)

            ctx_type = self.env.context.get('default_vehicle_purchase_type')
            ctx_service = self.env.context.get('default_fleet_purchase_service_code')
            ctx_document = self.env.context.get('default_fleet_document_id')

            if ctx_type and not vals.get('vehicle_purchase_type'):
                vals['vehicle_purchase_type'] = ctx_type

            if ctx_service and not vals.get('fleet_purchase_service_code'):
                vals['fleet_purchase_service_code'] = ctx_service

            if ctx_document and not vals.get('fleet_document_id'):
                vals['fleet_document_id'] = ctx_document

            service_code = vals.get('fleet_purchase_service_code') or ctx_service
            if vals.get('vehicle_purchase_type') == 'expense' and service_code:
                vals['observation'] = self._get_forced_observation_by_service(service_code)

            new_vals_list.append(vals)

        records = super().create(new_vals_list)

        for rec in records:
            rec._validate_forced_purchase_configuration()

            if rec.vehicle_id and rec.vehicle_purchase_type in ('contract', 'leasing_contract') and not rec.is_leasing_bill_order:
                rec._ensure_vehicle_contract_line()

            if rec.vehicle_id and not rec.partner_id and rec.vehicle_id.dealer_id:
                rec.partner_id = rec.vehicle_id.dealer_id.id

            if rec.vehicle_purchase_type == 'expense':
                rec._sync_vignette_visite_amounts_from_lines()
                rec._sync_expense_order_line_from_services()
                rec._sync_related_documents_with_purchase()

            if not rec.partner_ref:
                rec.partner_ref = rec._generate_unique_partner_ref()

        return records

    def write(self, vals):
        vals = dict(vals)

        if 'vehicle_purchase_type' in vals:
            vals.pop('vehicle_purchase_type')

        ctx_type = self.env.context.get('default_vehicle_purchase_type')
        ctx_service = self.env.context.get('default_fleet_purchase_service_code')
        ctx_document = self.env.context.get('default_fleet_document_id')

        if ctx_service:
            vals['fleet_purchase_service_code'] = ctx_service
            vals['observation'] = self._get_forced_observation_by_service(ctx_service)

        if ctx_document and not vals.get('fleet_document_id'):
            vals['fleet_document_id'] = ctx_document

        if 'vehicle_id' in vals and not self.env.context.get('allow_vehicle_purchase_edit'):
            for rec in self:
                if rec.vehicle_purchase_type in ('contract', 'leasing_contract') and not rec.is_leasing_bill_order:
                    raise ValidationError(_("Le véhicule n'est pas modifiable sur un contrat véhicule."))

        res = super().write(vals)

        if self.env.context.get('skip_vehicle_reapply'):
            return res

        for rec in self:
            extra_vals = {}

            if ctx_type and rec.vehicle_purchase_type != ctx_type:
                extra_vals['vehicle_purchase_type'] = ctx_type

            if ctx_service and rec.fleet_purchase_service_code != ctx_service:
                extra_vals['fleet_purchase_service_code'] = ctx_service

            if ctx_service:
                forced_obs = rec._get_forced_observation_by_service(ctx_service)
                if rec.observation != forced_obs:
                    extra_vals['observation'] = forced_obs

            if ctx_document and rec.fleet_document_id.id != ctx_document:
                extra_vals['fleet_document_id'] = ctx_document

            if extra_vals:
                super(PurchaseOrder, rec.with_context(skip_vehicle_reapply=True)).write(extra_vals)

            rec._validate_forced_purchase_configuration()

            if rec.vehicle_id and rec.vehicle_purchase_type in ('contract', 'leasing_contract') and not rec.is_leasing_bill_order:
                rec._ensure_vehicle_contract_line()

            if rec.vehicle_purchase_type == 'expense':
                rec._sync_vignette_visite_amounts_from_lines()
                rec._sync_expense_order_line_from_services()
                rec._sync_related_documents_with_purchase()

            if not rec.partner_ref:
                rec.partner_ref = rec._generate_unique_partner_ref()

        return res

    def button_confirm(self):
        card_service_codes = ('jawaz', 'carburant')

        self.filtered(
            lambda po: not po.is_leasing_bill_order
        )._ensure_vehicle_contract_line()

        # =========================
        # SYNCHRO MONTANTS AVANT CONFIRMATION
        # =========================
        for rec in self:
            if rec.vehicle_purchase_type == 'expense' and rec.fleet_purchase_service_code in (
                'assurance',
                'vignette',
                'visite_technique',
                'jawaz',
                'carburant',
                'carte_verte',
                'immatriculation',
                'penalite',
                'permis_circulation',
                'carte_grise'
            ):

                # =========================
                # CAS CARTES
                # =========================
                if rec.fleet_purchase_service_code in card_service_codes:

                    if not rec.rental_card_id:
                        raise ValidationError(_("Veuillez sélectionner une carte."))

                    rec._sync_expense_order_line_from_services()

                    total_amount = rec.card_amount_ttc or rec.card_amount_ht or 0.0

                    if total_amount <= 0:
                        raise ValidationError(_(
                            "Veuillez renseigner un montant pour la recharge."
                        ))

                    continue

                # =========================
                # CAS DOCUMENTS
                # =========================
                selected_lines = rec._get_service_vehicle_lines()

                for line in selected_lines:
                    if line.document_id and (not line.amount or line.amount <= 0):
                        line.amount = line.document_id.amount or 0.0

                rec._sync_vignette_visite_amounts_from_lines()
                rec._sync_expense_order_line_from_services()

                total_amount = sum(selected_lines.mapped('amount'))

                if total_amount <= 0:
                    total_amount = sum(
                        rec.order_line.filtered(
                            lambda l: not l.display_type
                        ).mapped('price_unit')
                    )

                if total_amount <= 0:
                    raise ValidationError(_(
                        "Impossible de confirmer ce bon de commande : le montant est à 0."
                    ))

        res = super().button_confirm()

        Document = self.env['fleet.vehicle.document']
        Tracking = self.env['fleet.location.tracking']

        for rec in self:

            # =========================
            # CONTRAT / LEASING
            # =========================
            if rec.vehicle_purchase_type in ('contract', 'leasing_contract') and not rec.is_leasing_bill_order:

                valid_lines = rec.order_line.filtered(
                    lambda l: not l.display_type
                )

                if not valid_lines:
                    raise ValidationError(_("Le contrat véhicule doit contenir une ligne produit."))

                if any(not line.product_id for line in valid_lines):
                    raise ValidationError(_("Le contrat véhicule contient une ligne sans produit."))

                if any(not line.product_uom_id for line in valid_lines):
                    raise ValidationError(_("Le contrat véhicule contient une ligne sans unité de mesure."))

                if rec.vehicle_id:

                    rec.vehicle_id.flush_recordset([
                        'assurance_first_name',
                        'assurance_first_date_start',
                        'assurance_first_date_end',
                        'assurance_first_state',
                        'vignette_first_name',
                        'vignette_first_date_start',
                        'vignette_first_date_end',
                        'vignette_first_state',
                        'visite_first_name',
                        'visite_first_date_start',
                        'visite_first_date_end',
                        'visite_first_state',
                        'permis_first_name',
                        'permis_first_date_start',
                        'permis_first_date_end',
                        'permis_first_state',
                    ])

                    rec.vehicle_id._create_all_first_manual_documents_from_vehicle()

                    manual_docs = Document.search([
                        ('vehicle_id', '=', rec.vehicle_id.id),
                        ('document_type', 'in', (
                            'assurance',
                            'vignette',
                            'visite',
                            'permis_circulation',
                        )),
                        ('auto_generated', '=', False),
                    ], order='date_start asc, id asc')

                    for doc_type in (
                        'assurance',
                        'vignette',
                        'visite',
                        'permis_circulation'
                    ):

                        doc = manual_docs.filtered(
                            lambda d: d.document_type == doc_type
                        )[:1]

                        if not doc:
                            continue

                        if not doc.source_purchase_order_id:
                            doc.with_context(
                                skip_document_state_sync=True
                            ).write({
                                'source_purchase_order_id': rec.id
                            })

                        doc.generate_missing_periodic_lines_after_approval()

                    rec.vehicle_id._update_vehicle_state_by_rules()

                if (
                    rec.vehicle_purchase_type == 'leasing_contract'
                    and not rec.is_leasing_bill_order
                    and hasattr(rec, 'action_generate_leasing_echeancier')
                    and hasattr(rec, 'leasing_echeance_ids')
                    and not rec.leasing_echeance_ids
                ):
                    rec.action_generate_leasing_echeancier()

            # =========================
            # CARTES
            # =========================
            if rec.vehicle_purchase_type == 'expense' and rec.fleet_purchase_service_code in (
                'jawaz',
                'carburant'
            ):

                if not rec.rental_card_id:
                    raise ValidationError(_("Veuillez sélectionner une carte."))

                # =========================
                # UPDATE CARTE
                # =========================
                rec.rental_card_id.write({
                    'amount': rec.card_amount_ttc,
                    'start_date': fields.Date.context_today(rec),
                })

                # =========================
                # TRACKING
                # =========================
                Tracking.create({
                    'name': rec.name,
                    'nature_operation': 'depense',
                    'type_operation': rec.fleet_purchase_service_code,
                    'service_code': rec.fleet_purchase_service_code,
                    'date_operation': fields.Date.context_today(rec),
                    'partner_id': rec.partner_id.id if rec.partner_id else False,
                    'product_id': rec.order_line[:1].product_id.id if rec.order_line[:1].product_id else False,
                    'montant_ht': rec.card_amount_ht,
                    'taxe': rec.card_tax_amount,
                    'montant_ttc': rec.card_amount_ttc,
                    'purchase_order_id': rec.id,
                    'source_model': 'purchase.order',
                    'source_res_id': rec.id,
                    'note': _('Recharge carte %s') % (
                        rec.fleet_purchase_service_code
                    ),
                })

                continue

            # =========================
            # EXPENSE DOCUMENTS
            # =========================
            if rec.vehicle_purchase_type == 'expense' and rec.fleet_purchase_service_code in (
                'assurance',
                'vignette',
                'visite_technique',
                'immatriculation',
                'penalite',
                'permis_circulation',
                'carte_grise'
            ):

                selected_lines = rec._get_service_vehicle_lines()

                if not selected_lines:
                    raise ValidationError(_("Ajoute au moins un véhicule."))

                if any(not line.vehicle_id for line in selected_lines):
                    raise ValidationError(_("Chaque ligne doit contenir un véhicule."))

                lines_requiring_document = selected_lines.filtered(
                    lambda l: l.service_code != 'penalite'
                )

                if any(not line.document_id for line in lines_requiring_document):
                    raise ValidationError(_("Chaque ligne doit contenir un document."))

                invalid_year_lines = lines_requiring_document.filtered(
                    lambda l:
                        l.document_id
                        and rec.service_document_year
                        and l.document_id.document_year != rec.service_document_year
                )

                if invalid_year_lines:
                    raise ValidationError(_(
                        "Tous les documents doivent appartenir à l'année choisie."
                    ))

                for line in selected_lines:
                    if line.document_id and (not line.amount or line.amount <= 0):
                        line.amount = line.document_id.amount or 0.0

                rec._sync_vignette_visite_amounts_from_lines()
                rec._sync_expense_order_line_from_services()
                rec._sync_related_documents_with_purchase()

        return res
    def button_approve(self, force=False):
        self.filtered(lambda po: not po.is_leasing_bill_order)._ensure_vehicle_contract_line()

        expense_orders = self.filtered(lambda po: po.vehicle_purchase_type == 'expense')
        expense_orders._sync_vignette_visite_amounts_from_lines()
        expense_orders._sync_expense_order_line_from_services()
        expense_orders._sync_related_documents_with_purchase()

        return super().button_approve(force=force)

    def action_confirm_leasing_contract(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract' and not rec.is_leasing_bill_order:
                if rec.leasing_workflow_state == 'draft':
                    rec.leasing_workflow_state = 'confirmed'
                    rec.leasing_contract_status = 'a_confirmer'

                    if rec.vehicle_id:
                        rec.vehicle_id._update_vehicle_state_by_rules()

        return True

    def action_approve_leasing_contract(self):
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract' and not rec.is_leasing_bill_order:
                if rec.leasing_workflow_state == 'confirmed':
                    rec.button_confirm()
                    rec.leasing_workflow_state = 'approved'
                    rec.leasing_contract_status = 'en_cours'
                    if rec.vehicle_id:
                        rec.vehicle_id._update_vehicle_state_by_rules()
        return True
    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        if not res.get('quantity') or res.get('quantity') <= 0:
            res['quantity'] = self.product_qty or 1.0
        return res
    def button_cancel(self):
        res = super().button_cancel()
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract' and not rec.is_leasing_bill_order:
                rec.leasing_workflow_state = 'cancel'
                rec.leasing_contract_status = 'a_confirmer'
        return res

    def button_draft(self):
        res = super().button_draft()
        for rec in self:
            if rec.vehicle_purchase_type == 'leasing_contract' and not rec.is_leasing_bill_order:
                rec.leasing_workflow_state = 'draft'
                rec.leasing_contract_status = 'a_confirmer'
        return res

    def action_create_bill_purchase_order_from_contract(self):
        self.ensure_one()

        if self.vehicle_purchase_type != 'leasing_contract':
            raise ValidationError(_("Cette action est réservée aux contrats leasing."))

        if self.is_leasing_bill_order:
            raise ValidationError(_("Cette action n'est pas autorisée sur un BL déjà issu d'un contrat ou d'une échéance."))

        if not self.vehicle_id:
            raise ValidationError(_("Veuillez sélectionner un véhicule."))

        if not self.leasing_company_id and not self.partner_id:
            raise ValidationError(_("Veuillez renseigner la société de leasing / fournisseur."))

        line_vals = self._prepare_vehicle_order_line_vals(self.vehicle_id)

        po_vals = {
            'partner_id': self.leasing_company_id.id or self.partner_id.id,
            'vehicle_id': self.vehicle_id.id,
            'vehicle_purchase_type': 'leasing_contract',
            'is_leasing_bill_order': True,
            'source_leasing_contract_id': self.id,
            'order_line': [(0, 0, line_vals)],
        }

        new_po = self.env['purchase.order'].create(po_vals)
        view = self.env.ref('your_module.view_purchase_order_leasing_bill_form_custom')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de commande'),
            'res_model': 'purchase.order',
            'res_id': new_po.id,
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'target': 'current',
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    allowed_product_ids = fields.Many2many(
        'product.product',
        related='order_id.allowed_product_ids',
        string="Produits autorisés",
        readonly=True
    )

    @api.onchange('order_id', 'product_id')
    def _onchange_allowed_products(self):
        domain = [('purchase_ok', '=', True)]

        if self.order_id:
            if self.order_id.vehicle_purchase_type in ('contract', 'leasing_contract'):
                if self.order_id.is_leasing_bill_order:
                    domain = [('purchase_ok', '=', True)]
                elif self.order_id.vehicle_id and self.order_id.vehicle_id.product_id:
                    domain = [('id', '=', self.order_id.vehicle_id.product_id.id)]
                else:
                    domain = [('id', '=', 0)]

            elif self.order_id.vehicle_purchase_type == 'expense':
                if self.order_id.fleet_purchase_service_code:
                    domain = [
                        ('purchase_ok', '=', True),
                        ('product_tmpl_id.fleet_service_type_id.service_code', '=', self.order_id.fleet_purchase_service_code)
                    ]

        if self.product_id:
            products = self.env['product.product'].search(domain)
            if self.product_id not in products:
                self.product_id = False

        return {'domain': {'product_id': domain}}

    @api.constrains('product_id', 'order_id')
    def _check_product_matches_order_type(self):
        for rec in self:
            if not rec.product_id or not rec.order_id:
                continue

            if rec.order_id.vehicle_purchase_type in ('contract', 'leasing_contract'):
                if rec.order_id.is_leasing_bill_order:
                    continue

                if rec.order_id.vehicle_id and rec.order_id.vehicle_id.product_id:
                    if rec.product_id != rec.order_id.vehicle_id.product_id:
                        raise ValidationError(_("Le produit sélectionné n'est pas autorisé pour ce type d'achat."))

            elif rec.order_id.vehicle_purchase_type == 'expense':
                code = rec.order_id.fleet_purchase_service_code
                if code:
                    product_code = rec.product_id.product_tmpl_id.fleet_service_type_id.service_code
                    if product_code != code:
                        raise ValidationError(_("Le produit sélectionné n'est pas autorisé pour ce type d'achat."))


class PurchaseOrderServiceVehicle(models.Model):
    _name = 'purchase.order.service.vehicle'
    _description = 'Véhicules liés à un achat service flotte'
    _order = 'id'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Achat",
        required=True,
        ondelete='cascade'
    )
    purchase_document_year = fields.Integer(
            related='purchase_order_id.service_document_year',
            string="Année",
            readonly=True
    )
    service_code = fields.Selection([
        ('assurance', 'Assurance'),
        ('vignette', 'Vignette'),
        ('visite_technique', 'Visite technique'),
        ('jawaz', 'Jawaz'),
        ('carburant', 'Carburant'),
        ('carte_verte', 'Carte verte'),
        ('immatriculation', 'Frais immatriculation'),
        ('penalite', 'Pénalités'),
        ('permis_circulation', 'Permis de circulation'),
        ('carte_grise', 'Carte grise'),
    ], string="Type service", required=True)

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        required=True
    )
    license_plate = fields.Char(
        string="Immatriculation",
        related='vehicle_id.license_plate',
        store=True,
        readonly=True,
    )

    numero_w = fields.Char(
        string="Numéro W",
        related='vehicle_id.numero_w',
        store=True,
        readonly=True,
    )

    model_name = fields.Char(
        string="Modèle",
        related='vehicle_id.model_name',
        store=True,
        readonly=True,
    )

    brand_name = fields.Char(
        string="Marque",
        related='vehicle_id.brand_name',
        store=True,
        readonly=True,
    )
    document_id = fields.Many2one(
        'fleet.vehicle.document',
        string="Document à payer"
    )

    note = fields.Char(string="Note")
    amount = fields.Float(string="Montant HT")

    document_count = fields.Integer(
        string="Documents non payés",
        compute="_compute_document_count"
    )

    tax_amount = fields.Float(
        string="Taxe",
        compute="_compute_vehicle_amounts",
        store=True
    )

    amount_ttc = fields.Float(
        string="Montant TTC",
        compute="_compute_vehicle_amounts",
        store=True
    )

    @api.depends('vehicle_id', 'service_code', 'purchase_order_id.service_document_year')
    def _compute_document_count(self):
        Document = self.env['fleet.vehicle.document']
        mapping = {
            'assurance': ['assurance'],
            'vignette': ['vignette'],
            'visite_technique': ['visite', 'visite_technique'],
            'jawaz': ['jawaz'],
            'carburant': ['carburant'],
            'carte_verte': ['carte_verte'],
            'immatriculation': ['immatriculation'],
            'penalite': ['penalite'],
            'permis_circulation': ['permis_circulation'],
            'carte_grise': ['carte_grise'],
        }

        for rec in self:
            rec.document_count = 0
            if not rec.vehicle_id or not rec.service_code:
                continue

            doc_types = mapping.get(rec.service_code, [rec.service_code])

            domain = [
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('document_type', 'in', doc_types),
                ('state', '=', 'not_paid'),
            ]

            if rec.purchase_document_year:
                domain.append(('document_year', '=', rec.purchase_document_year))

            rec.document_count = Document.search_count(domain)

    @api.onchange('vehicle_id', 'service_code', 'purchase_document_year')
    def _onchange_vehicle_id_service_code_document(self):
        self.document_id = False

        if not self.vehicle_id or not self.service_code:
            return {'domain': {'document_id': []}}

        mapping = {
            'assurance': ['assurance'],
            'vignette': ['vignette'],
            'visite_technique': ['visite', 'visite_technique'],
            'jawaz': ['jawaz'],
            'carburant': ['carburant'],
            'carte_verte': ['carte_verte'],
            'immatriculation': ['immatriculation'],
            'penalite': ['penalite'],
            'permis_circulation': ['permis_circulation'],
            'carte_grise': ['carte_grise'],
        }

        doc_types = mapping.get(self.service_code, [self.service_code])

        domain = [
            ('vehicle_id', '=', self.vehicle_id.id),
            ('document_type', 'in', doc_types),
            ('state', '=', 'not_paid'),
        ]

        if self.purchase_document_year:
            domain.append(('document_year', '=', self.purchase_document_year))

        return {
            'domain': {
                'document_id': domain
            }
        }

    @api.onchange('document_id')
    def _onchange_document_id_set_amount(self):
        for rec in self:
            if rec.document_id:
                rec.amount = rec.document_id.amount or 0.0

    @api.depends(
        'amount',
        'purchase_order_id.order_line.tax_ids',
        'purchase_order_id.order_line.tax_ids.amount'
    )
    def _compute_vehicle_amounts(self):
        for rec in self:
            tax_percent = 0.0

            main_order_line = rec.purchase_order_id.order_line.filtered(lambda l: not l.display_type)[:1]
            if main_order_line and main_order_line.tax_ids:
                tax_percent = sum(main_order_line.tax_ids.mapped('amount'))

            rec.tax_amount = (rec.amount or 0.0) * tax_percent / 100.0
            rec.amount_ttc = (rec.amount or 0.0) + rec.tax_amount

    _sql_constraints = [
        (
            'purchase_service_vehicle_unique',
            'unique(purchase_order_id, service_code, vehicle_id)',
            'Ce véhicule est déjà ajouté pour ce service dans cet achat.'
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        fixed_vals_list = []

        for vals in vals_list:
            vals = dict(vals)

            if not vals.get('service_code'):
                service_code = self.env.context.get('default_service_code')

                if not service_code and vals.get('purchase_order_id'):
                    order = self.env['purchase.order'].browse(vals['purchase_order_id'])
                    if order.exists():
                        service_code = order.fleet_purchase_service_code

                if service_code:
                    vals['service_code'] = service_code

            fixed_vals_list.append(vals)

        records = super().create(fixed_vals_list)

        orders = records.mapped('purchase_order_id')
        if orders:
            orders._sync_vignette_visite_amounts_from_lines()
            orders._sync_expense_order_line_from_services()
            orders._sync_related_documents_with_purchase()

        return records

    def write(self, vals):
        vals = dict(vals)

        if not vals.get('service_code'):
            for rec in self:
                if not rec.service_code:
                    vals['service_code'] = (
                        self.env.context.get('default_service_code')
                        or rec.purchase_order_id.fleet_purchase_service_code
                    )
                    break

        res = super().write(vals)

        orders = self.mapped('purchase_order_id')
        if orders:
            orders._sync_vignette_visite_amounts_from_lines()
            orders._sync_expense_order_line_from_services()
            orders._sync_related_documents_with_purchase()

        return res

    def unlink(self):
        orders = self.mapped('purchase_order_id')
        res = super().unlink()
        if orders:
            orders._sync_vignette_visite_amounts_from_lines()
            orders._sync_expense_order_line_from_services()
            orders._sync_related_documents_with_purchase()
        return res