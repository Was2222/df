# -*- coding: utf-8 -*-
# =============================================================================
# fleet_rental_crm / models / crm_lead_rental.py
# =============================================================================

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import math

_logger = logging.getLogger(__name__)


class CrmLeadRental(models.Model):
    _inherit = 'crm.lead'

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    # ─── RÉFÉRENCE RÉSERVATION ───────────────────────────────────────────────

    rental_reference = fields.Char(
        string="Référence réservation",
        index=True,
        help="Référence unique",
    )

    # ─── SOURCE DE L'OPPORTUNITÉ ─────────────────────────────────────────────

    lead_source = fields.Selection(
        selection=[
            ('website',      'Site web'),
            ('social_media', 'Réseaux sociaux'),
            ('crc',          'CRC (Centre de relation client)'),
            ('phone',        'Téléphone'),
            ('other',        'Autre'),
        ],
        string="Source de l'opportunité",
        tracking=True,
        index=True,
        help="Canal par lequel cette opportunité a été générée.",
    )

    # ─── STATUT RÉSERVATION ───────────────────────────────────────────────────

    reservation_status = fields.Selection(
        selection=[
            ('initial',  'Initial'),
            ('converti', 'Converti en contrat'),
            ('annule',   'Annulé'),
        ],
        string="Statut réservation",
        default='initial',
        tracking=True,
        copy=False,
        index=True,
    )

    # ─── CHAMPS VÉHICULE ─────────────────────────────────────────────────────

    vehicle_category_id = fields.Many2one(
        comodel_name='fleet.vehicle.model.category',
        string="Catégorie véhicule",
        tracking=True,
    )

    contract_type = fields.Selection(
        selection=[
            ('short',  'Courte durée'),
            ('medium', 'Moyenne durée'),
            ('long',   'Longue durée'),
        ],
        string="Type de contrat",
        default='short',
        help="Type de contrat de location souhaité",
    )

    # ─── PÉRIODE DE LOCATION ─────────────────────────────────────────────────

    rent_start_datetime = fields.Datetime(
        string="Début de la location",
        help="Date et heure de début souhaitées pour la location",
        tracking=True,
    )

    rent_end_datetime = fields.Datetime(
        string="Fin de la location",
        help="Date et heure de fin souhaitées pour la location",
        tracking=True,
    )

    number_of_days = fields.Integer(
        string="Nombre de jours",
        compute='_compute_number_of_days',
        store=True,
        help="Nombre de jours calculé automatiquement entre début et fin",
    )
    number_of_months = fields.Float(
        string="Nombre de mois",
        compute='_compute_number_of_months',
        store=True,
        help="Nombre de mois calculé automatiquement si location moyenne/longue durée",
    )

    # ─── TARIFICATION ────────────────────────────────────────────────────────

    rental_price_ht = fields.Float(
        string="Tarif unitaire HT (DH/jour ou DH/mois)",
        help="Tarif journalier ou mensuel selon la durée de location",
        tracking=True,
    )

    rental_tariff_id = fields.Many2one(
        comodel_name='rental.tariff',
        string="Tarif applicable",
        tracking=True,
        domain="[('active', '=', True)]",
    )

    rental_vat_percent = fields.Float(
        string="TVA (%)",
        default=20.0,
        tracking=True,
    )
    discount_percent = fields.Float(
        string="Remise (%)",
        default=0.0,
        tracking=True,
    )

    rental_price_after_discount = fields.Float(
        string="Tarif unitaire remisé",
        compute='_compute_rental_totals',
        store=True,
        readonly=True,
    )

    estimated_total_ttc = fields.Float(
        string="Total TTC estimé (DH)",
        compute='_compute_rental_totals',
        store=True,
        help="Total TTC estimé = total HT + TVA",
    )
    rounded = fields.Boolean(
        string="Arrondi",
        default=False,
    )
    unit_price_after_discount = fields.Float(
        string="Prix unitaire après remise",
        compute='_compute_rental_totals',
        store=True,
        readonly=True,
        help="Prix unitaire après application de la remise",
    )

    estimated_total_ht = fields.Float(
        string="Total estimé HT (DH)",
        compute='_compute_rental_totals',
        store=True,
        readonly=True,
        help="Montant total estimé hors taxes",
    )

    # ─── NOTES ───────────────────────────────────────────────────────────────

    rental_notes = fields.Text(
        string="Notes de location",
        help="Informations complémentaires pour la réservation",
    )

    # ─── RÉSUMÉ DEVIS ────────────────────────────────────────────────────────

    rental_order_count = fields.Integer(
        string="Devis de location",
        compute='_compute_rental_order_data',
    )
    summary_vehicle_category = fields.Char(
        string="Catégorie véhicule",
        compute='_compute_rental_order_data',
        store=False,
    )
    summary_contract_type = fields.Char(
        string="Type de contrat",
        compute='_compute_rental_order_data',
        store=False,
    )
    summary_rent_start = fields.Datetime(
        string="Début location",
        compute='_compute_rental_order_data',
        store=False,
    )
    summary_rent_end = fields.Datetime(
        string="Fin location",
        compute='_compute_rental_order_data',
        store=False,
    )
    summary_number_of_days = fields.Integer(
        string="Durée (jours)",
        compute='_compute_rental_order_data',
        store=False,
    )
    summary_tariff_name = fields.Char(
        string="Tarif appliqué",
        compute='_compute_rental_order_data',
        store=False,
    )
    summary_total_ht = fields.Float(
        string="Total HT estimé (DH)",
        compute='_compute_rental_order_data',
        store=False,
    )

    # ─── LIEN CONTRAT FLEET ──────────────────────────────────────────────────

    fleet_contract_id = fields.Many2one(
        comodel_name='car.rental.contract',
        string="Contrat de location",
        copy=False,
        readonly=True,
        tracking=True,
    )
    fleet_contract_state = fields.Selection(
        related='fleet_contract_id.state',
        string="État du contrat",
        readonly=True,
    )
    fleet_contract_name = fields.Char(
        related='fleet_contract_id.name',
        string="Réf. contrat",
        readonly=True,
        store=True,
    )

    estimated_daily_rate = fields.Float(
        string="Tarif journalier estimé (DH)",
        compute='_compute_estimated_daily_rate',
        inverse='_inverse_estimated_daily_rate',
        store=False,
        help="Ancien champ - utiliser 'Tarif unitaire HT' à la place",
    )

    # ─── MÉTHODES DE CALCUL ──────────────────────────────────────────────────

    @api.depends('rent_start_datetime', 'rent_end_datetime')
    def _compute_number_of_days(self):
        for order in self:
            if order.rent_start_datetime and order.rent_end_datetime:
                start_date = order.rent_start_datetime.date()
                end_date = order.rent_end_datetime.date()
                days = (end_date - start_date).days + 1
                order.number_of_days = max(days, 0)
            else:
                order.number_of_days = 0

    @api.depends('rent_start_datetime', 'rent_end_datetime', 'contract_type')
    def _compute_number_of_months(self):
        for record in self:
            if record.contract_type in ('medium', 'long') and record.number_of_days > 0:
                days = record.number_of_days
                months_rounded = round(days / 30.0)
                if months_rounded > 0 and (28 * months_rounded) <= days <= (31 * months_rounded):
                    record.number_of_months = months_rounded
                else:
                    record.number_of_months = round(days / 30.0, 2)
            else:
                record.number_of_months = 0

    def _apply_rounding(self, amount):
        if not self.rounded:
            return amount
        if amount < 1000:
            return math.ceil(amount / 10.0) * 10
        return math.ceil(amount / 100.0) * 100

    @api.depends('rental_price_ht', 'discount_percent', 'number_of_days',
                 'number_of_months', 'contract_type', 'rental_vat_percent', 'rounded')
    def _compute_rental_totals(self):
        for record in self:
            rate_remise = record.rental_price_ht * (1 - record.discount_percent / 100.0)
            record.rental_price_after_discount = rate_remise

            if record.contract_type == 'short':
                total_ht = rate_remise * record.number_of_days
            else:
                total_ht = rate_remise * record.number_of_months

            total_ht = record._apply_rounding(total_ht)
            total_ttc = record._apply_rounding(
                total_ht * (1 + record.rental_vat_percent / 100.0)
            )

            record.estimated_total_ht = total_ht
            record.estimated_total_ttc = total_ttc

    @api.depends('rental_price_ht', 'contract_type')
    def _compute_estimated_daily_rate(self):
        for record in self:
            record.estimated_daily_rate = record.rental_price_ht

    def _inverse_estimated_daily_rate(self):
        for record in self:
            if record.estimated_daily_rate:
                record.rental_price_ht = record.estimated_daily_rate

    @api.depends(
        'order_ids', 'order_ids.is_rental_order',
        'order_ids.state', 'order_ids.rental_tariff_id',
        'order_ids.rent_start_datetime', 'order_ids.rent_end_datetime',
        'order_ids.rental_total_ht', 'order_ids.is_contract_converted',
    )
    def _compute_rental_order_data(self):
        for lead in self:
            rental_orders = lead.order_ids.filtered(lambda o: o.is_rental_order)
            lead.rental_order_count = len(rental_orders)

            # Priorité : devis converti > confirmé (sale) > envoyé (sent) > dernier
            best = rental_orders.sorted(
                key=lambda o: (
                    0 if o.is_contract_converted
                    else 1 if o.state == 'sale'
                    else 2 if o.state == 'sent'
                    else 3,
                    -(o.id or 0),
                )
            )[:1]

            if best:
                order = best[0]
                lead.summary_vehicle_category = (
                    order.vehicle_category_id.name if order.vehicle_category_id else '—'
                )
                lead.summary_contract_type = dict(
                    order._fields['contract_type'].selection
                ).get(order.contract_type, '—')
                lead.summary_rent_start     = order.rent_start_datetime
                lead.summary_rent_end       = order.rent_end_datetime
                lead.summary_number_of_days = order.number_of_days
                lead.summary_tariff_name    = (
                    order.rental_tariff_id.name if order.rental_tariff_id else '—'
                )
                lead.summary_total_ht       = order.rental_total_ht
            else:
                lead.summary_vehicle_category = '—'
                lead.summary_contract_type    = '—'
                lead.summary_rent_start       = False
                lead.summary_rent_end         = False
                lead.summary_number_of_days   = 0
                lead.summary_tariff_name      = '—'
                lead.summary_total_ht         = 0.0

    # ─── SURCHARGE DU COMPTEUR NATIF ─────────────────────────────────────────

    @api.depends(
        'order_ids.state',
        'order_ids.is_rental_order',
        'order_ids.currency_id',
        'order_ids.amount_untaxed',
        'order_ids.date_order',
        'order_ids.company_id',
    )
    def _compute_sale_data(self):
        super()._compute_sale_data()

        for lead in self:
            rental_orders = lead.order_ids.filtered(lambda o: o.is_rental_order)
            if not rental_orders:
                continue

            classic_draft_sent = lead.order_ids.filtered(
                lambda o: not o.is_rental_order and o.state in ('draft', 'sent', 'sale', 'cancel')
            )
            lead.sale_order_count = len(rental_orders) + len(classic_draft_sent)

    # ─── CONTRAINTES DE VALIDATION ───────────────────────────────────────────

    @api.constrains('rent_start_datetime', 'rent_end_datetime')
    def _check_rental_dates(self):
        for record in self:
            if record.rent_start_datetime and record.rent_end_datetime:
                if record.rent_end_datetime <= record.rent_start_datetime:
                    raise ValidationError(_(
                        "La date de fin de location doit être postérieure à la date de début."
                    ))

    @api.constrains('reservation_status')
    def _check_reservation_status_transition(self):
        for lead in self:
            if lead.reservation_status == 'annule' and lead.fleet_contract_id:
                raise ValidationError(_(
                    "Impossible de passer en 'Annulé' : un contrat (%s) est lié à cette réservation."
                ) % lead.fleet_contract_id.name)

    # ─── HELPER : résolution robuste des stages ──────────────────────────────

    def _get_crm_stage(self, xmlid, name_keywords):
        stage = self.env.ref(xmlid, raise_if_not_found=False)
        if not stage:
            for kw in name_keywords:
                stage = self.env['crm.stage'].search(
                    [('name', 'ilike', kw)], limit=1
                )
                if stage:
                    _logger.info(
                        "Stage '%s' résolu par recherche nom '%s' (id=%s)",
                        xmlid, kw, stage.id,
                    )
                    break
        if not stage:
            _logger.warning(
                "Stage introuvable pour xmlid='%s' / mots-clés=%s — stage_id non mis à jour.",
                xmlid, name_keywords,
            )
        return stage

    # ─── HELPER : devis de location principal ────────────────────────────────

    def _get_main_rental_order(self):
        self.ensure_one()
        rental_orders = self.order_ids.filtered(lambda o: o.is_rental_order)
        if not rental_orders:
            raise UserError(_(
                "Aucun devis de location n'est lié à cette opportunité.\n\n"
                "Créez d'abord un devis en cochant 'Devis de location', "
                "puis renseignez la catégorie, la période et le tarif."
            ))
        return rental_orders.sorted(
            key=lambda o: (
                0 if o.is_contract_converted
                else 1 if o.state == 'sale'
                else 2 if o.state == 'sent'
                else 3,
                -(o.id or 0),
            )
        )[0]

    # ─── HELPER : produit de location selon type de contrat ──────────────────

    def _get_rental_product_for_order_line(self):
        """
        Retourne le produit de service à utiliser dans les lignes du devis,
        selon le type de contrat (short / medium / long).
        """
        self.ensure_one()
        xml_id_map = {
            'short':  'fleet_rental.fleet_service_product_short',
            'medium': 'fleet_rental.fleet_service_product_medium',
            'long':   'fleet_rental.fleet_service_product_long',
        }
        xml_id = xml_id_map.get(self.contract_type or 'short')
        product = self.env.ref(xml_id, raise_if_not_found=False)

        if not product:
            name_map = {
                'short':  'Courte Durée',
                'medium': 'Moyenne Durée',
                'long':   'Longue Durée',
            }
            label = name_map.get(self.contract_type or 'short', '')
            if label:
                product = self.env['product.product'].search(
                    [('name', 'ilike', label), ('type', '=', 'service')], limit=1
                )
            if not product:
                product = self.env['product.product'].search(
                    [('name', 'ilike', 'Location'), ('type', '=', 'service')], limit=1
                )

        return product

    # ─── CALLBACKS DÉCLENCHÉS DEPUIS sale.order ───────────────────────────────

    def _on_rental_order_sent(self, order):
        """
        Déclenché quand un devis de location lié passe en état 'sent'.
        → Étape 3 : Proposition
        """
        self.ensure_one()

        if self.reservation_status in ('converti', 'annule'):
            return

        stage_proposition = self._get_crm_stage(
            'fleet_rental_crm.crm_stage_rental_proposition',
            ['Proposition', 'Devis envoyé', 'Offre'],
        )

        if stage_proposition:
            write_vals['stage_id'] = stage_proposition.id
        self.write(write_vals)

        self.message_post(body=_(
            "📤 <b>Devis envoyé au client</b><br/>"
            "Devis : <b>%s</b><br/>"
            "Statut réservation : <b>Initial</b> → en attente de confirmation client."
        ) % order.name)

    def _on_rental_order_confirmed(self, order):
        """
        Déclenché quand un devis de location lié passe en état 'sale'.
        → Étape 4 : Confirmé
        """
        self.ensure_one()

        if self.reservation_status in ('converti', 'annule'):
            return

        sync_vals = {}

        if order.vehicle_category_id:
            sync_vals['vehicle_category_id'] = order.vehicle_category_id.id
        if order.contract_type:
            sync_vals['contract_type'] = order.contract_type
        if order.rent_start_datetime:
            sync_vals['rent_start_datetime'] = order.rent_start_datetime
        if order.rent_end_datetime:
            sync_vals['rent_end_datetime'] = order.rent_end_datetime
        if order.rental_price_ht:
            sync_vals['estimated_daily_rate'] = order.rental_price_ht
        if order.discount_percent is not None:
            sync_vals['discount_percent'] = order.discount_percent

        
        self.write(sync_vals)

        self.message_post(body=_(
            "✅ <b>Réservation confirmée</b><br/>"
            "Le devis <b>%s</b> a été confirmé.<br/><br/>"
            "<b>Données de location synchronisées :</b><br/>"
            "• Catégorie : %s<br/>"
            "• Type contrat : %s<br/>"
            "• Période : %s → %s (%s jours)<br/>"
            "• Tarif : %.2f DH/j | Remise : %.1f%%<br/>"
            "• <b>Total HT : %.2f DH</b>"
        ) % (
            order.name,
            order.vehicle_category_id.name if order.vehicle_category_id else '—',
            dict(order._fields['contract_type'].selection).get(order.contract_type, '—'),
            order.rent_start_datetime.strftime('%d/%m/%Y %H:%M') if order.rent_start_datetime else '—',
            order.rent_end_datetime.strftime('%d/%m/%Y %H:%M') if order.rent_end_datetime else '—',
            order.number_of_days,
            order.rental_price_ht,
            order.discount_percent,
            order.rental_total_ht,
        ))

        _logger.info(
            "Lead #%s : réservation confirmée depuis devis %s. "
            "Données synchronisées : %s",
            self.id, order.name, list(sync_vals.keys()),
        )

    # ─── VÉRIFICATIONS ───────────────────────────────────────────────────────

    def _check_prerequisites_for_confirmation(self):
        self.ensure_one()
        errors = []

        if not self.vehicle_category_id:
            errors.append(_("• Catégorie véhicule non renseignée"))

        if not self.rent_start_datetime or not self.rent_end_datetime:
            errors.append(_("• Dates de location manquantes"))
        elif self.rent_end_datetime <= self.rent_start_datetime:
            errors.append(_("• Dates invalides (fin ≤ début)"))

        if not self.estimated_daily_rate:
            errors.append(_("• Tarif journalier non renseigné"))

        if self.vehicle_category_id and self.rent_start_datetime and self.rent_end_datetime:
            conflicts = self.env['car.rental.contract'].search([
                ('state', '=', 'lance'),
                ('category_invoiced', '=', self.vehicle_category_id.id),
                ('rent_start_datetime', '<', self.rent_end_datetime),
                ('rent_end_datetime', '>', self.rent_start_datetime),
            ])
            if conflicts:
                errors.append(_(
                    "• Conflit de disponibilité : catégorie '%s' "
                    "occupée sur la période (contrat : %s)"
                ) % (self.vehicle_category_id.name, conflicts[0].name))

        if errors:
            raise UserError(_(
                "Impossible de confirmer la réservation.\n\n"
                "Contrôles obligatoires non satisfaits :\n%s"
            ) % '\n'.join(errors))

    # ─── ACTIONS WORKFLOW ────────────────────────────────────────────────────

    @api.onchange('vehicle_category_id', 'contract_type', 'rent_start_datetime',
                  'rent_end_datetime', 'partner_id')
    def _onchange_fetch_tariff(self):
        if not self.vehicle_category_id or not self.contract_type:
            return

        duration_days = None
        if self.rent_start_datetime and self.rent_end_datetime:
            delta = self.rent_end_datetime - self.rent_start_datetime
            days = delta.days + (1 if delta.seconds > 0 else 0)
            duration_days = max(days, 0)

        tariff = self.env['rental.tariff'].get_applicable_tariff(
            contract_date=self.rent_start_datetime or fields.Datetime.now(),
            contract_type=self.contract_type,
            vehicle_category_id=self.vehicle_category_id.id,
            customer_id=self.partner_id.id if self.partner_id else None,
            duration_days=duration_days,
        )

        if tariff:
            self.rental_tariff_id = tariff.id
            self.rental_price_ht = tariff.rental_price_ht
            self.rental_vat_percent = tariff.vat_percent
        else:
            self.rental_tariff_id = False
            return {
                'warning': {
                    'title': _('Aucun tarif trouvé'),
                    'message': _(
                        "Aucun tarif actif pour :\n"
                        "• Catégorie : %s\n"
                        "• Type contrat : %s\n"
                        "• Durée : %s jours\n\n"
                        "Saisissez le prix HT manuellement ou créez un tarif."
                    ) % (
                        self.vehicle_category_id.name,
                        dict(self._fields['contract_type'].selection).get(
                            self.contract_type, self.contract_type),
                        duration_days or '—',
                    ),
                }
            }

    @api.onchange('rental_tariff_id')
    def _onchange_tariff_id(self):
        if self.rental_tariff_id:
            self.rental_price_ht = self.rental_tariff_id.rental_price_ht
            self.rental_vat_percent = self.rental_tariff_id.vat_percent

    # =========================================================================
    # MODIFIÉ : action_sale_quotations_new
    # Ajout automatique de la ligne de prestation dans le devis
    # =========================================================================
    def action_sale_quotations_new(self):
        """
        Étape 2 : Créer un devis de location.
        Ajoute automatiquement une ligne de service correspondant au type
        de contrat (Courte / Moyenne / Longue durée) avec le tarif et la
        quantité calculés depuis l'opportunité.
        """
        self.ensure_one()

        # ── Recherche du produit de service selon le type de contrat ──────
        product = self._get_rental_product_for_order_line()

        # ── Calcul du prix unitaire remisé ────────────────────────────────
        price_remise = self.rental_price_ht * (
            1.0 - (self.discount_percent or 0.0) / 100.0
        )

        if self.contract_type in ('medium', 'long'):
            duree = float(self.number_of_months) if self.number_of_months else 1.0
            unite = 'mois'
        else:
            duree = float(self.number_of_days) if self.number_of_days else 1.0
            unite = 'jour(s)'

        price_final = price_remise * duree
        qty = 1.0

        # ── Construction de la description de ligne ───────────────────────
        if product:
            line_name = product.name
            if self.vehicle_category_id:
                line_name = f"{product.name} – {self.vehicle_category_id.name}"
            if self.rent_start_datetime and self.rent_end_datetime:
                line_name += (
                    f"\n{self.rent_start_datetime.strftime('%d/%m/%Y %H:%M')} → "
                    f"{self.rent_end_datetime.strftime('%d/%m/%Y %H:%M')}"
                    f" (Durée : {duree} {unite})"
                )
            if self.rental_tariff_id:
                line_name += f"\nTarif : {self.rental_tariff_id.name}"

        # ── Lignes de commande ────────────────────────────────────────────
        order_lines = []
        if product:
            order_lines = [(0, 0, {
                'product_id':      product.id,
                'name':            line_name,
                'product_uom_qty': qty,
                'price_unit':      price_final,
            })]
        else:
            _logger.warning(
                "Lead #%s : aucun produit de service trouvé pour le type '%s'. "
                "Le devis sera créé sans ligne.",
                self.id, self.contract_type,
            )

        # ── Création du devis ─────────────────────────────────────────────
        sale_order = self.env['sale.order'].create({
            'partner_id':          self.partner_id.id,
            'opportunity_id':      self.id,
            'is_rental_order':     True,
            'state':               'draft',
            'vehicle_category_id': self.vehicle_category_id.id if self.vehicle_category_id else False,
            'contract_type':       self.contract_type or 'short',
            'rent_start_datetime': self.rent_start_datetime,
            'rent_end_datetime':   self.rent_end_datetime,
            'rental_price_ht':     self.rental_price_ht or 0.0,
            'discount_percent':    self.discount_percent or 0.0,
            'rental_tariff_id':    self.rental_tariff_id.id if self.rental_tariff_id else False,
            'rounded':             self.rounded,
            'rental_vat_percent':  self.rental_vat_percent,
            'order_line':          order_lines,
        })

        # ── Mise à jour du stage ──────────────────────────────────────────
        stage_proposition = self._get_crm_stage(
            'fleet_rental_crm.crm_stage_rental_proposition',
            ['Proposition', 'Devis envoyé', 'Offre'],
        )

        write_vals = {}
        if stage_proposition:
            write_vals['stage_id'] = stage_proposition.id
        if write_vals:
            self.write(write_vals)

        self.message_post(body=_(
        "📋 <b>Devis de location créé</b><br/>"
        "Devis : <b>%s</b> | Réf. réservation : <b>%s</b> | Statut : Brouillon<br/>"
        "Prestation : %s<br/>"
        "Détails : %.2f DH × %d véhicule(s) (inclut la durée de %s %s)<br/>"
        "Total HT : %.2f DH"
    ) % (
        sale_order.name,
        self.rental_reference or '—',
        product.name if product else '—',
        price_remise,
        qty,
        duree,
        unite,
        price_final,
    ))

        return {
            'type':      'ir.actions.act_window',
            'name':      _('Devis de location'),
            'res_model': 'sale.order',
            'res_id':    sale_order.id,
            'view_mode': 'form',
            'target':    'current',
        }

    def action_confirm_reservation(self):
        self.ensure_one()

        if self.reservation_status == 'converti':
            raise UserError(_("Cette réservation a déjà été convertie en contrat."))
        if self.reservation_status == 'annule':
            raise UserError(_("Cette réservation est annulée. Réinitialisez-la d'abord."))
        

        self._check_prerequisites_for_confirmation()

        

        self.write(write_vals)

        if self.contract_type == 'short':
            unit_text = f"{self.rental_price_ht} DH/jour"
            period_text = f"{self.number_of_days} jours"
        else:
            unit_text = f"{self.rental_price_ht} DH/mois"
            period_text = f"{self.number_of_months:.1f} mois"

        self.message_post(body=_(
            "✅ <b>Réservation confirmée manuellement</b><br/>"
            "Client : %s | Catégorie : %s<br/>"
            "Période : %s → %s (%s)<br/>"
            "Tarif : %s | Remise : %.1f%%<br/>"
            "Total HT : %.2f DH | Total TTC : %.2f DH"
        ) % (
            self.partner_id.name if self.partner_id else '—',
            self.vehicle_category_id.name if self.vehicle_category_id else '—',
            self.rent_start_datetime.strftime('%d/%m/%Y %H:%M') if self.rent_start_datetime else '—',
            self.rent_end_datetime.strftime('%d/%m/%Y %H:%M') if self.rent_end_datetime else '—',
            period_text,
            unit_text,
            self.discount_percent,
            self.estimated_total_ht,
            self.estimated_total_ttc,
        ))
        return True

    def action_convert_to_contract(self):
        """
        Étape 5 : Ouvre le wizard de conversion.
        """
        self.ensure_one()

        

        if self.fleet_contract_id:
            raise UserError(_(
                "Un contrat existe déjà : %s\n"
                "Accédez-y via le bouton 'Voir le contrat'."
            ) % self.fleet_contract_id.name)

        if not self.partner_id:
            raise UserError(_("Le client est obligatoire pour créer un contrat."))

        rental_orders = self.order_ids.filtered(lambda o: o.is_rental_order and o.state == 'sale')
        best_order = rental_orders.sorted(key=lambda o: -o.id)[:1]

        if best_order:
            order = best_order[0]
            ctx_contract_type    = order.contract_type
            ctx_start            = order.rent_start_datetime
            ctx_end              = order.rent_end_datetime
            ctx_vehicle_category = order.vehicle_category_id.id if order.vehicle_category_id else False
            ctx_unit_price_ht    = order.rental_price_ht
            ctx_discount_percent = order.discount_percent
            ctx_rental_tariff    = order.rental_tariff_id.id if order.rental_tariff_id else False
            ctx_rounded          = order.rounded
            ctx_vat_percent      = order.rental_vat_percent
        else:
            ctx_contract_type    = self.contract_type
            ctx_start            = self.rent_start_datetime
            ctx_end              = self.rent_end_datetime
            ctx_vehicle_category = self.vehicle_category_id.id if self.vehicle_category_id else False
            ctx_unit_price_ht    = self.rental_price_ht
            ctx_discount_percent = self.discount_percent
            ctx_rental_tariff    = self.rental_tariff_id.id if self.rental_tariff_id else False
            ctx_rounded          = self.rounded
            ctx_vat_percent      = self.rental_vat_percent

        return {
            'type':      'ir.actions.act_window',
            'name':      _('Convertir en contrat'),
            'res_model': 'crm.rental.convert.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context': {
                'default_lead_id':              self.id,
                'default_customer_id':          self.partner_id.id,
                'default_contract_type':        ctx_contract_type,
                'default_rent_start_datetime':  ctx_start,
                'default_rent_end_datetime':    ctx_end,
                'default_vehicle_category_id':  ctx_vehicle_category,
                'default_unit_price_ht':        ctx_unit_price_ht,
                'default_discount_percent':     ctx_discount_percent,
                'default_rental_tariff_id':     ctx_rental_tariff,
                'default_rounded':              ctx_rounded,
                'default_vat_percent':          ctx_vat_percent,
            },
        }

    def _do_convert_to_contract(self, contract_vals=None, converted_order_id=None):
        """
        Crée le contrat de location et met à jour le lead.
        Appelé depuis le wizard de conversion.
        """
        self.ensure_one()

        if contract_vals is None:
            contract_vals = {}

        default_vals = {
            'customer_id':         self.partner_id.id,
            'contract_type':       contract_vals.get('contract_type') or self.contract_type,
            'rent_start_datetime': contract_vals.get('rent_start_datetime') or self.rent_start_datetime,
            'rent_end_datetime':   contract_vals.get('rent_end_datetime') or self.rent_end_datetime,
            'daily_rate':          contract_vals.get('daily_rate') or contract_vals.get('unit_price_ht') or self.rental_price_ht,
            'discount_percent':    contract_vals.get('discount_percent') or self.discount_percent,
            'rounded':             contract_vals.get('rounded') or self.rounded,
            'vat_percent':         contract_vals.get('vat_percent') or self.rental_vat_percent,
            'state':               'en_saisie',
            'notes': _(
                "Contrat généré depuis l'opportunité CRM : %s (Réf : %s)\n"
                "Période : %s → %s\n"
                "Type contrat : %s\n"
                "Tarif : %.2f DH/%s\n"
                "Total HT estimé : %.2f DH\n"
                "Total TTC estimé : %.2f DH"
            ) % (
                self.name,
                self.rental_reference or '—',
                self.rent_start_datetime.strftime('%d/%m/%Y') if self.rent_start_datetime else '—',
                self.rent_end_datetime.strftime('%d/%m/%Y') if self.rent_end_datetime else '—',
                dict(self._fields['contract_type'].selection).get(self.contract_type, self.contract_type),
                contract_vals.get('unit_price_ht') or self.rental_price_ht,
                'jour' if self.contract_type == 'short' else 'mois',
                contract_vals.get('estimated_total_ht') or self.estimated_total_ht,
                contract_vals.get('estimated_total_ttc') or self.estimated_total_ttc,
            ),
        }

        if self.vehicle_category_id:
            default_vals['category_invoiced'] = self.vehicle_category_id.id

        default_vals.update(contract_vals)

        keys_to_remove = [
            'rental_tariff_id', 'estimated_total_ht', 'estimated_total_ttc',
            'unit_price_ht', 'vat_percent', 'rounded',
            'number_of_days', 'number_of_months',
        ]
        for key in keys_to_remove:
            default_vals.pop(key, None)

        contract = self.env['car.rental.contract'].create(default_vals)

        if converted_order_id:
            self.env['sale.order'].browse(converted_order_id).write({
                'is_contract_converted': True,
            })
        else:
            rental_orders = self.order_ids.filtered(
                lambda o: o.is_rental_order and o.state == 'sale'
            )
            best = rental_orders.sorted(key=lambda o: -o.id)[:1]
            if best:
                best[0].write({'is_contract_converted': True})

        stage_converti = self._get_crm_stage(
            'fleet_rental_crm.crm_stage_rental_converti',
            ['Converti en contrat', 'Gagné', 'Won'],
        )

        write_vals = {
            'fleet_contract_id':  contract.id,
            'reservation_status': 'converti',
        }
        if stage_converti:
            write_vals['stage_id'] = stage_converti.id

        self.write(write_vals)

        self.message_post(body=_(
            "🎉 <b>Converti en contrat</b><br/>"
            "Contrat créé : <b>%s</b><br/>"
            "Réf. réservation : <b>%s</b><br/>"
            "Client : %s<br/>"
            "Période : %s → %s<br/>"
            "Total HT : %.2f DH | Total TTC : %.2f DH<br/>"
            "<i>Le contrat est en état 'En saisie'. "
            "Complétez-le (véhicule précis, documents…) puis lancez-le.</i>"
        ) % (
            contract.name,
            self.rental_reference or '—',
            contract.customer_id.name,
            contract.rent_start_datetime.strftime('%d/%m/%Y') if contract.rent_start_datetime else '—',
            contract.rent_end_datetime.strftime('%d/%m/%Y') if contract.rent_end_datetime else '—',
            contract_vals.get('estimated_total_ht', self.estimated_total_ht),
            contract_vals.get('estimated_total_ttc', self.estimated_total_ttc),
        ))

        _logger.info(
            "Opportunité CRM #%s (Réf: %s) convertie en contrat %s (stage_id=%s)",
            self.id, self.rental_reference, contract.name,
            write_vals.get('stage_id', 'non mis à jour'),
        )
        return contract

    def action_cancel_reservation(self):
        self.ensure_one()

        if self.reservation_status == 'converti':
            raise UserError(_(
                "Impossible d'annuler : réservation déjà convertie en contrat (%s).\n\n"
                "Pour annuler, gérez le contrat directement :\n"
                "• En saisie → réinitialisez le contrat\n"
                "• Lancé → clôturez le contrat"
            ) % (self.fleet_contract_id.name if self.fleet_contract_id else '—'))

        if self.reservation_status == 'annule':
            raise UserError(_("Cette réservation est déjà annulée."))

        stage_annule = self._get_crm_stage(
            'fleet_rental_crm.crm_stage_rental_annule',
            ['Annulé', 'Annule', 'Perdu', 'Lost'],
        )

        write_vals = {'reservation_status': 'annule'}
        if stage_annule:
            write_vals['stage_id'] = stage_annule.id

        self.write(write_vals)
        self.message_post(body=_(
            "❌ <b>Réservation annulée</b><br/>"
            "Le véhicule est de nouveau disponible pour cette période."
        ))
        return True

    def action_reset_to_initial(self):
        self.ensure_one()

        if self.reservation_status not in ('annule',):
            raise UserError(_(
                "Seules les réservations annulées peuvent être réinitialisées.\n"
                "Statut actuel : %s"
            ) % dict(self._fields['reservation_status'].selection).get(
                self.reservation_status, self.reservation_status
            ))

        self.write({'reservation_status': 'initial'})
        self.message_post(body=_("🔄 Réservation réinitialisée à l'état initial."))
        return True

    def action_view_contract(self):
        self.ensure_one()
        if not self.fleet_contract_id:
            raise UserError(_("Aucun contrat n'est encore associé à cette réservation."))
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Contrat de location'),
            'res_model': 'car.rental.contract',
            'res_id':    self.fleet_contract_id.id,
            'view_mode': 'form',
            'target':    'current',
        }

    def action_view_sale_quotations_with_onboarding(self):
        action = super().action_view_sale_quotations_with_onboarding()
        return action

    def action_view_sale_quotation(self):
        self.ensure_one()

        rental_orders = self.order_ids.filtered(lambda o: o.is_rental_order)

        if not rental_orders:
            return super().action_view_sale_quotation()

        all_rental_ids = rental_orders.ids

        classic_orders = self.order_ids.filtered(
            lambda o: not o.is_rental_order and o.state in ('draft', 'sent', 'sale', 'cancel')
        )

        combined_ids = all_rental_ids + classic_orders.ids

        if len(combined_ids) == 1:
            return {
                'type':      'ir.actions.act_window',
                'name':      _('Devis de location'),
                'res_model': 'sale.order',
                'res_id':    combined_ids[0],
                'view_mode': 'form',
                'target':    'current',
                'context': {
                    'default_opportunity_id':  self.id,
                    'default_partner_id':      self.partner_id.id,
                    'default_is_rental_order': True,
                },
            }

        return {
            'type':      'ir.actions.act_window',
            'name':      _('Devis / Commandes de location'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', combined_ids)],
            'target':    'current',
            'context': {
                'default_opportunity_id':  self.id,
                'default_partner_id':      self.partner_id.id,
                'default_is_rental_order': True,
            },
        }

    def _get_stage_mapping(self):
        mapping = {}

        definitions = [
            ('fleet_rental_crm.crm_stage_rental_converti', 'converti',
             ['Converti en contrat', 'Gagné', 'Won']),
            ('fleet_rental_crm.crm_stage_rental_annule', 'annule',
             ['Annulé', 'Annule', 'Perdu', 'Lost']),
            ('fleet_rental_crm.crm_stage_rental_proposition', 'proposition',
             ['Proposition', 'Devis envoyé', 'Offre']),
        ]

        for xmlid, status, keywords in definitions:
            stage = self._get_crm_stage(xmlid, keywords)
            if stage:
                mapping[stage.id] = status

        return mapping

    # ─── CONTRÔLE DES TRANSITIONS ───────────────────────────────────────
    def _check_stage_transition_allowed(self, new_stage_id):
        self.ensure_one()

        if self.type != 'opportunity':
            return

        if self.stage_id.id == new_stage_id:
            return

        stage_mapping = self._get_stage_mapping()
        target_status = stage_mapping.get(new_stage_id)

        # 🚫 Converti interdit via drag
      


        # ✅ Confirmé
        if target_status == 'converti':
           

            

            self._check_prerequisites_for_confirmation()

        # ❌ Annulé
        if target_status == 'annule':
            

            if self.reservation_status == 'annule':
                raise UserError(_("Déjà annulé."))

        # 🔒 Anti retour arrière
        ORDRE = ['initial', 'proposition', 'converti']

        if self.reservation_status in ORDRE and target_status in ORDRE:
            if ORDRE.index(target_status) < ORDRE.index(self.reservation_status):
                raise UserError(_("Retour arrière interdit."))

    # ─── SURCHARGE WRITE ────────────────────────────────────────────────
    def write(self, vals):

        if 'stage_id' in vals:
            new_stage_id = vals['stage_id']

            for lead in self:
                lead._check_stage_transition_allowed(new_stage_id)

            # Sync automatique statut
            stage_mapping = self._get_stage_mapping()
            target_status = stage_mapping.get(new_stage_id)

            if target_status in ['converti', 'annule'] and 'reservation_status' not in vals:
                vals['reservation_status'] = target_status

        return super().write(vals)