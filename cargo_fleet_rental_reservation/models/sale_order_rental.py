# -*- coding: utf-8 -*-
# =============================================================================
# fleet_rental_crm / models / sale_order_rental.py
# =============================================================================

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
import math

_logger = logging.getLogger(__name__)


class SaleOrderRental(models.Model):
    _inherit = 'sale.order'

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    is_rental_order = fields.Boolean(
        string="Devis de location",
        default=False,
        copy=True,
    )

    # ─── STATUT CONVERSION ────────────────────────────────────────────────────

    is_contract_converted = fields.Boolean(
        string="Converti en contrat",
        default=False,
        copy=False,
        readonly=True,
        index=True,
        help="Ce devis a été utilisé pour créer un contrat de location.",
    )

    # NOUVEAU : Statut d'approbation
    approval_status = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('pending', 'En attente d\'approbation'),
            ('approved', 'Approuvé'),
            ('rejected', 'Rejeté'),
        ],
        string="Statut approbation",
        default='draft',
        tracking=True,
        copy=False,
    )

    approved_by = fields.Many2one(
        'res.users',
        string="Approuvé par",
        readonly=True,
        copy=False,
    )

    approval_date = fields.Datetime(
        string="Date d'approbation",
        readonly=True,
        copy=False,
    )

    approval_notes = fields.Text(
        string="Notes d'approbation",
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Devis'),
            ('sent', 'Devis envoyé'),
            ('approved', 'Approuvé'),
            ('contract', 'Converti en contrat'),

            # Vente standard Odoo
            ('sale', 'Bon de commande'),
            ('done', 'Verrouillé'),

            ('cancel', 'Annulé'),
        ],
        string='Statut',
        readonly=True,
        copy=False,
        index=True,
        tracking=3,
        default='draft',
    )

    rental_quotation_status = fields.Selection(
        selection=[
            ('draft',     'Nouveau'),
            ('sent',      'Proposition'),
            ('won',       'Gagné'),
            ('lost',      'Perdu'),
        ],
        string="Statut location",
        compute='_compute_rental_quotation_status',
        store=True,
        help="Statut étendu du devis de location.",
    )

    # ─── RÉFÉRENCE DE L'OPPORTUNITÉ ───────────────────────────────────────────
   
    # This field pulls the value from the linked Opportunity (crm.lead)
    lead_rental_reference = fields.Char(
        string="Réf. réservation",
        related='opportunity_id.rental_reference',
        readonly=True,
        store=True,
        help="Référence unique de l'opportunité / réservation source.",
    )

    # If you also want a local reference field on the Sale Order itself:
    rental_reference = fields.Char(
        string="Référence réservation",
        index=True,
        help="Référence unique",
    )

    lead_source = fields.Selection(
        related='opportunity_id.lead_source',
        string="Source opportunité",
        readonly=True,
        store=False,
    )

    # ─── CONTRAT ASSOCIÉ ──────────────────────────────────────────────────────

    fleet_contract_id = fields.Many2one(
        comodel_name='car.rental.contract',
        string="Contrat associé",
        readonly=True,
        store=True,
        help="Contrat de location généré depuis ce devis.",
    )
    fleet_contract_state = fields.Selection(
    related='fleet_contract_id.state',
    string="État du contrat",
    readonly=True,
    store=False,  # Non stocké car c'est un related
)

    fleet_contract_name = fields.Char(
        string="Réf. contrat",
        related='fleet_contract_id.name',
        readonly=True,
        store=True,
    )

    rental_reference = fields.Char(
        string="Réf. location",
        compute='_compute_rental_reference',
        store=True,
        help="Référence de location (héritée de l'opportunité ou du devis).",
    )

    # ─── VÉHICULE ─────────────────────────────────────────────────────────────

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
        tracking=True,
    )

    # ─── PÉRIODE ──────────────────────────────────────────────────────────────

    rent_start_datetime = fields.Datetime(string="Date de début", tracking=True)
    rent_end_datetime   = fields.Datetime(string="Date de fin",   tracking=True)

    number_of_days = fields.Integer(
        string="Durée (jours)",
        compute='_compute_number_of_days',
        store=True,
        readonly=True,
    )
    number_of_months = fields.Float(
        string="Durée (mois)",
        compute='_compute_number_of_months',
        store=True,
        readonly=True,
    )

    # ─── TARIF ────────────────────────────────────────────────────────────────

    rental_tariff_id = fields.Many2one(
        comodel_name='rental.tariff',
        string="Tarif applicable",
        tracking=True,
        domain="[('active', '=', True)]",
    )
    rental_tariff_unit = fields.Selection(
        related='rental_tariff_id.unit',
        string="Unité",
        readonly=True,
    )
    rental_price_ht = fields.Float(
        string="Prix unitaire HT (DH/j ou mois)",
        tracking=True,
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
    rounded = fields.Boolean(
        string="Arrondi",
        default=False,
    )

    # ─── TOTAUX ───────────────────────────────────────────────────────────────

    rental_price_after_discount = fields.Float(
        string="Prix unitaire HT remisé",
        compute='_compute_rental_totals',
        store=True,
        readonly=True,
    )
    rental_total_ht = fields.Float(
        string="Total HT location (DH)",
        compute='_compute_rental_totals',
        store=True,
        readonly=True,
    )
    rental_total_ttc = fields.Float(
        string="Total TTC location (DH)",
        compute='_compute_rental_totals',
        store=True,
        readonly=True,
    )

    rental_notes = fields.Text(string="Notes location")

    advance_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Paiement d'avance",
        copy=False,
        readonly=True,
        help="Paiement d'avance lié à ce devis",
    )

    advance_payment_ref = fields.Char(
        string="Référence paiement",
        related='advance_payment_id.name',
        readonly=True,
        store=True,
    )

    advance_payment_date = fields.Date(
        string="Date paiement avance",
        related='advance_payment_id.date',
        readonly=True,
        store=True,
    )

    advance_amount = fields.Monetary(
        string="Montant avance (DH)",
        related='advance_payment_id.amount',
        currency_field='currency_id',
        store=True,
        readonly=True,
    )

    # ─── COMPUTE RENTAL REFERENCE ────────────────────────────────────────────

    @api.depends('lead_rental_reference', 'name')
    def _compute_rental_reference(self):
        for order in self:
            order.rental_reference = order.lead_rental_reference or order.name

    # ─── COMPUTE STATUT LOCATION ──────────────────────────────────────────────

    @api.depends('state', 'is_contract_converted', 'is_rental_order', 'approval_status')
    def _compute_rental_quotation_status(self):
        for order in self:
            if not order.is_rental_order:
                order.rental_quotation_status = False
                continue
            if order.state == 'cancel' or order.approval_status == 'rejected':
                order.rental_quotation_status = 'lost'
                continue
            if order.fleet_contract_id and order.fleet_contract_state == 'annule':
                order.rental_quotation_status = 'lost'
                continue
            if order.is_contract_converted:
                order.rental_quotation_status = 'won'
            elif order.state == 'cancel':
                order.rental_quotation_status = 'lost'
            elif order.state == 'sent':
                order.rental_quotation_status = 'sent'
            else:
                order.rental_quotation_status = 'draft'

    # ─── ARRONDI ──────────────────────────────────────────────────────────────

    def _apply_rounding(self, amount):
        self.ensure_one()
        if not self.rounded:
            return amount
        if amount < 1000:
            return math.ceil(amount / 10.0) * 10
        return math.ceil(amount / 100.0) * 100

    # ─── COMPUTE ──────────────────────────────────────────────────────────────

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

    @api.depends('number_of_days')
    def _compute_number_of_months(self):
        for order in self:
            if order.number_of_days <= 0:
                order.number_of_months = 0
                continue
            days = order.number_of_days
            months_rounded = round(days / 30.0)
            if months_rounded > 0 and (28 * months_rounded) <= days <= (31 * months_rounded):
                order.number_of_months = months_rounded
            else:
                order.number_of_months = round(days / 30.0, 2)

    @api.depends(
        'rental_price_ht', 'discount_percent', 'number_of_days',
        'number_of_months', 'contract_type', 'rental_vat_percent', 'rounded',
    )
    def _compute_rental_totals(self):
        for order in self:
            rate_remise = order.rental_price_ht * (1 - order.discount_percent / 100.0)
            order.rental_price_after_discount = rate_remise

            if order.contract_type == 'short':
                total_ht = rate_remise * order.number_of_days
            else:
                total_ht = rate_remise * order.number_of_months

            total_ht  = order._apply_rounding(total_ht)
            total_ttc = order._apply_rounding(
                total_ht * (1 + order.rental_vat_percent / 100.0)
            )

            order.rental_total_ht  = total_ht
            order.rental_total_ttc = total_ttc

    # ─── VALIDATION AVANT APPROBATION ─────────────────────────────────────────

    def _validate_before_approval(self):
        """Vérifie que tous les champs requis sont remplis avant approbation"""
        self.ensure_one()
        errors = []

        if not self.vehicle_category_id:
            errors.append("• Catégorie véhicule non renseignée")
        
        if not self.contract_type:
            errors.append("• Type de contrat non renseigné")
        
        if not self.rent_start_datetime:
            errors.append("• Date de début non renseignée")
        
        if not self.rent_end_datetime:
            errors.append("• Date de fin non renseignée")
        
        if self.rent_start_datetime and self.rent_end_datetime:
            if self.rent_end_datetime <= self.rent_start_datetime:
                errors.append("• Date de fin doit être postérieure à la date de début")
        
        if not self.rental_price_ht or self.rental_price_ht <= 0:
            errors.append("• Prix unitaire HT doit être supérieur à 0")
        
        if errors:
            raise UserError(_(
                "❌ Impossible d'approuver le devis\n\n"
                "Veuillez compléter les informations suivantes :\n%s"
            ) % '\n'.join(errors))

    # ─── ACTIONS D'APPROBATION ────────────────────────────────────────────────

    def action_submit_approval(self):
        """
        Soumettre le devis pour approbation
        """
        for order in self:
            if not order.is_rental_order:
                raise UserError(_("Seuls les devis de location peuvent être soumis pour approbation."))
            
            if order.approval_status != 'draft':
                raise UserError(_("Ce devis a déjà été soumis ou approuvé."))
            if order.opportunity_id and order.opportunity_id.fleet_contract_id:
                raise UserError(_(
                "❌ Soumission impossible\n\n"
                "Cette opportunité a déjà un contrat converti : %s\n\n"
                "Une opportunité ne peut avoir qu'un seul contrat.\n\n"
                "Actions possibles :\n"
                "• Créez une nouvelle opportunité pour ce devis\n"
                "• Utilisez l'opportunité existante sans contrat\n"
                "• Annulez le contrat existant si nécessaire"
            ) % order.opportunity_id.fleet_contract_id.name)

            # Validation basique
            order._validate_before_approval()
            
            # Passage en attente d'approbation
            order.write({
                'approval_status': 'pending',
                'state': 'sent',  # État proposition
            })
            
            # Notification au responsable (à implémenter selon vos besoins)
            order.message_post(body=_(
                "📋 <b>Devis soumis pour approbation</b><br/>"
                "En attente de validation par un responsable.<br/>"
                "Total HT : %.2f DH | Total TTC : %.2f DH"
            ) % (order.rental_total_ht, order.rental_total_ttc))
            
            if order.opportunity_id:
                order.opportunity_id.message_post(body=_(
                    "📋 Devis <b>%s</b> soumis pour approbation"
                ) % order.name)

    def action_approve(self):
        """
        Approuver le devis par un responsable
        """
        for order in self:
            if not order.is_rental_order:
                raise UserError(_("Seuls les devis de location peuvent être approuvés."))
            
            if order.approval_status != 'pending':
                raise UserError(_("Seuls les devis en attente d'approbation peuvent être approuvés."))
            if order.opportunity_id and order.opportunity_id.fleet_contract_id:
                raise UserError(_(
                "❌ Approbation impossible\n\n"
                "Cette opportunité a déjà un contrat converti : %s\n\n"
                "Impossible d'approuver un nouveau devis pour une opportunité qui a déjà un contrat.\n\n"
                "Actions possibles :\n"
                "• Créez une nouvelle opportunité pour ce devis\n"
                "• Ou annulez le contrat existant si vous souhaitez le remplacer"
            ) % order.opportunity_id.fleet_contract_id.name)
        
       
            # Vérification finale avant approbation
            order._validate_before_approval()
            
            # Approbation
            order.write({
                'approval_status': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            
            order.message_post(body=_(
                "✅ <b>Devis approuvé</b><br/>"
                "Approuvé par : %s<br/>"
                "Le devis peut maintenant être converti en contrat."
            ) % self.env.user.name)
            
            if order.opportunity_id:
                order.opportunity_id.message_post(body=_(
                    "✅ Devis <b>%s</b> approuvé par %s"
                ) % (order.name, self.env.user.name))

    def action_reject(self):
        """
        Rejeter le devis
        """
        view_id = self.env.ref('fleet_rental_crm.view_rejection_reason_wizard').id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Motif du rejet'),
            'res_model': 'rental.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }

    def _do_reject(self, reason):
        """Exécute le rejet avec motif"""
        self.ensure_one()
        
        self.write({
            'approval_status': 'rejected',
            'state': 'cancel',
            'approval_notes': reason,
        })
        
        self.message_post(body=_(
            "❌ <b>Devis rejeté</b><br/>"
            "Motif : %s"
        ) % reason)
        
        if self.opportunity_id:
            self.opportunity_id.message_post(body=_(
                "❌ Devis <b>%s</b> rejeté<br/>Motif : %s"
            ) % (self.name, reason))

    # ─── ONCHANGE ─────────────────────────────────────────────────────────────

    @api.onchange(
        'vehicle_category_id', 'contract_type',
        'rent_start_datetime', 'rent_end_datetime', 'partner_id',
    )
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
            self.rental_tariff_id   = tariff.id
            self.rental_price_ht    = tariff.rental_price_ht
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
            self.rental_price_ht    = self.rental_tariff_id.rental_price_ht
            self.rental_vat_percent = self.rental_tariff_id.vat_percent

    @api.onchange('rent_start_datetime', 'rent_end_datetime')
    def _onchange_validate_period(self):
        if (self.rent_start_datetime and self.rent_end_datetime
                and self.rent_end_datetime <= self.rent_start_datetime):
            return {
                'warning': {
                    'title': _('Dates invalides'),
                    'message': _("La date de fin doit être postérieure à la date de début."),
                }
            }

    # ─── CONTRAINTES ──────────────────────────────────────────────────────────

    @api.constrains('rent_start_datetime', 'rent_end_datetime')
    def _check_rental_dates(self):
        for order in self:
            if (order.rent_start_datetime and order.rent_end_datetime
                    and order.rent_end_datetime <= order.rent_start_datetime):
                raise ValidationError(_(
                    "La date de fin doit être postérieure à la date de début."
                ))

    # ─── OVERRIDE SUPPRESSION BOUTON CONFIRMER ────────────────────────────────

    def action_confirm(self):
        for order in self:
            if order.is_rental_order:
                raise UserError(_(
                    "❌ Action non disponible\n\n"
                    "Les devis de location suivent un workflow spécifique :\n"
                    "1. Remplir le devis\n"
                    "2. Soumettre pour approbation\n"
                    "3. Après approbation, convertir en contrat\n\n"
                    "Le bouton 'Confirmer' est désactivé pour ce type de devis."
                ))

            if order.vehicle_id:
                for line in order.order_line:
                    product = line.product_id
                    if product and product.invoice_policy != 'order':
                        product.product_tmpl_id.write({
                            'invoice_policy': 'order'
                        })

        res = super().action_confirm()

        for order in self:
            if order.vehicle_id and not order.is_rental_order:
                order.order_line._compute_invoice_status()
                order._compute_invoice_status()

        return res

    def action_cancel(self):
        """Annulation du devis avec vérification"""
        for order in self:
            if order.is_rental_order and order.is_contract_converted:
                raise UserError(_(
                    "Impossible d'annuler ce devis car il a déjà été converti en contrat.\n"
                    "Contrat associé : %s" % order.fleet_contract_id.name
                ))
            if order.is_rental_order and order.approval_status == 'approved':
                raise UserError(_(
                    "❌ Impossible d'annuler un devis approuvé.\n"
                    "Si vous ne souhaitez pas convertir ce devis, veuillez le rejeter d'abord."
                ))
        return super().action_cancel()

    def copy(self, default=None):
        """Empêche la duplication d'un devis converti ou approuvé"""
        if self.is_contract_converted:
            raise UserError(_(
                "Ce devis a déjà été converti en contrat.\n"
                "Impossible de le dupliquer."
            ))
        if self.approval_status == 'approved':
            raise UserError(_(
                "Ce devis est approuvé.\n"
                "Impossible de le dupliquer, vous pouvez créer un nouveau devis à la place."
            ))
        return super().copy(default)

    # ─── ACTIONS CONVERSION ───────────────────────────────────────────────────

    def action_convert_to_contract(self):
        """
        Ouvre le wizard de conversion en contrat depuis le devis de location.
        UNIQUEMENT pour les devis approuvés.
        """
        self.ensure_one()

        if not self.is_rental_order:
            raise UserError(_("Ce devis n'est pas un devis de location."))

        # Vérification cruciale : seulement les devis approuvés
        if self.approval_status != 'approved':
            raise UserError(_(
                "❌ Conversion impossible\n\n"
                "Le devis doit être approuvé avant d'être converti en contrat.\n"
                "Statut actuel : %s\n\n"
                "Étapes à suivre :\n"
                "1. Remplir toutes les informations\n"
                "2. Cliquer sur 'Soumettre pour approbation'\n"
                "3. Un responsable doit approuver le devis\n"
                "4. Ensuite seulement, vous pourrez convertir en contrat"
            ) % dict(self._fields['approval_status'].selection).get(
                self.approval_status, self.approval_status
            ))

        if self.is_contract_converted:
            raise UserError(_(
                "Ce devis a déjà été converti en contrat.\n"
                "Consultez le contrat lié."
            ))

        if not self.opportunity_id:
            raise UserError(_(
                "Ce devis n'est pas lié à une opportunité CRM.\n"
                "La conversion en contrat nécessite une opportunité source."
            ))

        lead = self.opportunity_id

        if lead.fleet_contract_id:
            raise UserError(_(
                "Un contrat existe déjà pour cette opportunité : %s\n"
                "Un seul contrat peut être créé par opportunité."
            ) % lead.fleet_contract_id.name)

        return {
            'type':      'ir.actions.act_window',
            'name':      _('Convertir en contrat'),
            'res_model': 'crm.rental.convert.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context': {
                'default_lead_id':              lead.id,
                'default_customer_id':          self.partner_id.id,
                'default_contract_type':        self.contract_type,
                'default_rent_start_datetime':  self.rent_start_datetime,
                'default_rent_end_datetime':    self.rent_end_datetime,
                'default_vehicle_category_id':  self.vehicle_category_id.id if self.vehicle_category_id else False,
                'default_unit_price_ht':        self.rental_price_ht,
                'default_discount_percent':     self.discount_percent,
                'default_rental_tariff_id':     self.rental_tariff_id.id if self.rental_tariff_id else False,
                'default_rounded':              self.rounded,
                'default_vat_percent':          self.rental_vat_percent,
                'default_source_order_id':      self.id,
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

        reservation_value = False
        if self.opportunity_id:
            reservation_value = (
            self.opportunity_id.rental_reference or 
            self.opportunity_id.name or 
            f"OPP-{self.opportunity_id.id}"
        )


        notes_text = _(
        "Contrat généré depuis le devis de location : %s\n"
        "Opportunité source : %s\n"
        "Période : %s → %s\n"
        "Type contrat : %s\n"
        "Tarif : %.2f DH/%s\n"
        "Total HT estimé : %.2f DH\n"
        "Total TTC estimé : %.2f DH"
    ) % (
        self.name,  # 1
        self.opportunity_id.name if self.opportunity_id else '—',  # 2
        self.rent_start_datetime.strftime('%d/%m/%Y') if self.rent_start_datetime else '—',  # 3
        self.rent_end_datetime.strftime('%d/%m/%Y') if self.rent_end_datetime else '—',  # 4
        dict(self._fields['contract_type'].selection).get(self.contract_type, self.contract_type),  # 5
        contract_vals.get('unit_price_ht') or self.rental_price_ht,  # 6 (%.2f)
        'jour' if self.contract_type == 'short' else 'mois',  # 7
        contract_vals.get('estimated_total_ht') or self.rental_total_ht,  # 8 (%.2f)
        contract_vals.get('estimated_total_ttc') or self.rental_total_ttc,  # 9 (%.2f)
    )



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
            'source_quotation_id': self.id,  # Lien vers le devis source
            'reservation':         reservation_value,
            'opportunity_id':      self.opportunity_id.id if self.opportunity_id else False,
            'notes': notes_text,
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

        # Marquer le devis comme converti et lier le contrat
        self.write({
            'is_contract_converted': True,
            'fleet_contract_id': contract.id,
        })

        if self.opportunity_id:
            stage_won = self.opportunity_id._get_crm_stage(
                'fleet_rental_crm.crm_stage_rental_won',
                ['Gagné', 'Won', 'Converti'],
            )

            write_vals = {
                'fleet_contract_id': contract.id,
                'reservation_status': 'converti',
            }
            if stage_won:
                write_vals['stage_id'] = stage_won.id

            self.opportunity_id.write(write_vals)

            self.opportunity_id.message_post(body=_(
                "🎉 <b>Converti en contrat</b><br/>"
                "Contrat créé : <b>%s</b><br/>"
                "Depuis le devis : <b>%s</b><br/>"
                "Client : %s<br/>"
                "Période : %s → %s<br/>"
                "Total HT : %.2f DH | Total TTC : %.2f DH"
            ) % (
                contract.name,
                self.name,
                contract.customer_id.name,
                contract.rent_start_datetime.strftime('%d/%m/%Y') if contract.rent_start_datetime else '—',
                contract.rent_end_datetime.strftime('%d/%m/%Y') if contract.rent_end_datetime else '—',
                contract_vals.get('estimated_total_ht', self.rental_total_ht),
                contract_vals.get('estimated_total_ttc', self.rental_total_ttc),
            ))

        _logger.info(
            "Devis #%s converti en contrat %s",
            self.id, contract.name,
        )
        return contract

    def action_view_rental_contract(self):
        """Ouvre le contrat lié depuis le devis."""
        self.ensure_one()
        if not self.fleet_contract_id:
            raise UserError(_("Aucun contrat n'est associé à ce devis de location."))
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Contrat de location'),
            'res_model': 'car.rental.contract',
            'res_id':    self.fleet_contract_id.id,
            'view_mode': 'form',
            'target':    'current',
        }

    # ─── UTILITAIRE ───────────────────────────────────────────────────────────

    def get_rental_data_for_contract(self):
        self.ensure_one()
        return {
            'contract_type':        self.contract_type,
            'rent_start_datetime':  self.rent_start_datetime,
            'rent_end_datetime':    self.rent_end_datetime,
            'vehicle_category_id':  self.vehicle_category_id.id if self.vehicle_category_id else False,
            'daily_rate':           self.rental_price_ht,
            'discount_percent':     self.discount_percent,
            'rental_tariff_id':     self.rental_tariff_id.id if self.rental_tariff_id else False,
            'rounded':              self.rounded,
            'number_of_days':       self.number_of_days,
            'number_of_months':     self.number_of_months,
        }

    @api.depends('is_rental_order', 'rental_total_ht', 'order_line.price_total')
    def _compute_amount_total(self):
        super()._compute_amount_total()
        for order in self:
            if order.is_rental_order:
                order.amount_untaxed = order.rental_total_ht
                order.amount_total = order.rental_total_ttc


    def action_print_quotation(self):
        return self.env.ref('sale.action_report_saleorder').report_action(self)

    def action_preview_sale_order(self):
        return self.env.ref('sale.action_report_saleorder').report_action(self, config=False)