# -*- coding: utf-8 -*-
# =============================================================================
# fleet_rental_crm / wizard / convert_to_contract_wizard.py
#
# Wizard de conversion d'un devis approuvé en contrat de location.
# Étape finale du workflow : Devis approuvé → Contrat
# =============================================================================

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math
import logging

_logger = logging.getLogger(__name__)


class CrmRentalConvertWizard(models.TransientModel):
    _name = 'crm.rental.convert.wizard'
    _description = 'Wizard de conversion en contrat de location'

    # ─── LIENS ────────────────────────────────────────────────────────────────

    lead_id = fields.Many2one(
        'crm.lead',
        string="Opportunité",
        required=True,
        readonly=True,
    )

    source_order_id = fields.Many2one(
        'sale.order',
        string="Devis source",
        readonly=True,
        help="Devis approuvé à l'origine de cette conversion",
    )

    lead_name = fields.Char(
        string="Nom de l'opportunité",
        related='lead_id.name',
        readonly=True,
    )

    lead_rental_reference = fields.Char(
        string="Réf. réservation",
        related='lead_id.rental_reference',
        readonly=True,
    )

    customer_id = fields.Many2one(
        'res.partner',
        string="Client",
        required=True,
        readonly=True,
    )

    # ─── DONNÉES CONTRAT ──────────────────────────────────────────────────────

    contract_type = fields.Selection(
        selection=[
            ('short',  'Courte durée'),
            ('medium', 'Moyenne durée'),
            ('long',   'Longue durée'),
        ],
        string="Type de contrat",
        required=True,
    )

    rent_start_datetime = fields.Datetime(
        string="Date de début",
        required=True,
    )

    rent_end_datetime = fields.Datetime(
        string="Date de fin",
        required=True,
    )

    number_of_days = fields.Integer(
        string="Nombre de jours",
        compute='_compute_number_of_days',
        store=True,
        readonly=True,
    )

    number_of_months = fields.Float(
        string="Nombre de mois",
        compute='_compute_number_of_months',
        store=True,
        readonly=True,
    )

    vehicle_category_id = fields.Many2one(
        'fleet.vehicle.model.category',
        string="Catégorie véhicule",
    )

    rental_tariff_id = fields.Many2one(
        'rental.tariff',
        string="Tarif appliqué",
        readonly=True,
    )

    # ─── TARIFICATION ────────────────────────────────────────────────────────

    unit_price_ht = fields.Float(
        string="Prix unitaire HT",
        required=True,
        help="Tarif journalier (courte durée) ou mensuel (moyenne/longue durée)",
    )

    discount_percent = fields.Float(
        string="Remise (%)",
        default=0.0,
    )

    rounded = fields.Boolean(
        string="Arrondi",
        default=False,
    )

    vat_percent = fields.Float(
        string="TVA (%)",
        default=20.0,
    )

    unit_price_after_discount = fields.Float(
        string="Prix unitaire après remise",
        compute='_compute_amounts',
        store=True,
        readonly=True,
    )

    estimated_total_ht = fields.Float(
        string="Total estimé HT (DH)",
        compute='_compute_amounts',
        store=True,
        readonly=True,
    )

    estimated_total_ttc = fields.Float(
        string="Total estimé TTC (DH)",
        compute='_compute_amounts',
        store=True,
        readonly=True,
    )

    # ─── AVANCE DE PAIEMENT ───────────────────────────────────────────────────

    advance_required = fields.Boolean(
        string="Avance obligatoire",
        compute='_compute_advance_required',
        help="L'avance est obligatoire pour les contrats de courte et moyenne durée.",
    )

    advance_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Paiement d'avance",
        domain="[('partner_id', 'child_of', customer_id),"
               " ('state', '=', 'in_process'),"
               " ('payment_consumption_state', '=', 'unconsumed'),"
               " ('payment_type', '=', 'inbound'),"
               " ('fleet_rent_id', '=', False),"
               " ('has_allocated_invoices', '=', False)]",
        help="Paiements clients validés, sans facture allouée, non encore liés à un contrat de location.",
    )

    advance_amount = fields.Monetary(
        string="Montant de l'avance",
        related='advance_payment_id.amount',
        readonly=True,
        currency_field='currency_id',
    )

    advance_payment_date = fields.Date(
        string="Date du paiement",
        related='advance_payment_id.date',
        readonly=True,
    )

    advance_payment_ref = fields.Char(
        string="Référence paiement",
        related='advance_payment_id.name',
        readonly=True,
    )

    advance_notes = fields.Text(
        string="Observations sur l'avance",
        help="Informations complémentaires sur l'avance (optionnel).",
    )

    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id,readonly=True,)
    source_order_approved_by = fields.Char(
    string="Approuvé par",
    related='source_order_id.approved_by.name',
    readonly=True,
)
    source_order_approval_date = fields.Datetime(
    string="Date d'approbation",
    related='source_order_id.approval_date',
    readonly=True,
)



    # ─── CALCULS ──────────────────────────────────────────────────────────────

    @api.depends('contract_type')
    def _compute_advance_required(self):
        for rec in self:
            rec.advance_required = rec.contract_type in ('short', 'medium')

    @api.depends('rent_start_datetime', 'rent_end_datetime')
    def _compute_number_of_days(self):
        for record in self:
            if record.rent_start_datetime and record.rent_end_datetime:
                start_date = record.rent_start_datetime.date()
                end_date = record.rent_end_datetime.date()
                days = (end_date - start_date).days + 1
                record.number_of_days = max(days, 0)
            else:
                record.number_of_days = 0

    @api.depends('number_of_days', 'contract_type')
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

    @api.depends('unit_price_ht', 'discount_percent', 'number_of_days',
                 'number_of_months', 'contract_type', 'rounded', 'vat_percent')
    def _compute_amounts(self):
        for record in self:
            discount_factor = 1 - (record.discount_percent / 100.0)
            unit_price_after_discount = record.unit_price_ht * discount_factor
            record.unit_price_after_discount = unit_price_after_discount

            if record.contract_type == 'short':
                total_ht = unit_price_after_discount * record.number_of_days
            else:
                total_ht = unit_price_after_discount * record.number_of_months

            total_ht = record._apply_rounding(total_ht)
            total_ttc = record._apply_rounding(
                total_ht * (1 + record.vat_percent / 100.0)
            )

            record.estimated_total_ht = total_ht
            record.estimated_total_ttc = total_ttc

    # ─── VALIDATION ───────────────────────────────────────────────────────────

    def _validate_before_conversion(self):
        self.ensure_one()
        errors = []

        # Vérification que le devis est approuvé
        if self.source_order_id:
            if self.source_order_id.approval_status != 'approved':
                errors.append(_(
                    "❌ Le devis source n'est pas approuvé.\n"
                    "Statut actuel : %s\n\n"
                    "Seuls les devis approuvés peuvent être convertis en contrat."
                ) % dict(self.source_order_id._fields['approval_status'].selection).get(
                    self.source_order_id.approval_status, self.source_order_id.approval_status
                ))
            
            if self.source_order_id.is_contract_converted:
                errors.append(_(
                    "❌ Ce devis a déjà été converti en contrat.\n"
                    "Contrat existant : %s" % self.source_order_id.fleet_contract_id.name
                ))

        if self.lead_id.reservation_status == 'converti':
            errors.append(_(
                "Cette opportunité a déjà été convertie en contrat.\n"
                "Contrat existant : %s" % self.lead_id.fleet_contract_id.name
            ))

        # Avance obligatoire pour courte/moyenne durée
        if self.advance_required and not self.advance_payment_id:
            errors.append(_(
                "💳 Paiement d'avance obligatoire.\n"
                "Veuillez sélectionner un paiement client existant pour les contrats "
                "de courte ou moyenne durée.\n"
                "Si aucun paiement n'est disponible, enregistrez d'abord "
                "le paiement dans la comptabilité."
            ))

        # Vérification de la cohérence des dates
        if self.rent_start_datetime and self.rent_end_datetime:
            if self.rent_end_datetime <= self.rent_start_datetime:
                errors.append(_("• Les dates sont invalides (date de fin ≤ date de début)."))
        else:
            errors.append(_("• Les dates de début et de fin sont obligatoires."))

        # Vérification du tarif
        if not self.unit_price_ht or self.unit_price_ht <= 0:
            errors.append(_("• Le prix unitaire HT doit être supérieur à 0."))

        # Vérification des quantités
        if self.contract_type == 'short':
            if self.number_of_days <= 0:
                errors.append(_("• La durée de location (jours) doit être supérieure à 0."))
        else:
            if self.number_of_months <= 0:
                errors.append(_("• La durée de location (mois) doit être supérieure à 0."))

        # Vérification qu'un contrat n'existe pas déjà
        if self.lead_id.fleet_contract_id:
            errors.append(_(
                "• Un contrat existe déjà : %s"
            ) % self.lead_id.fleet_contract_id.name)

        # Vérification que le paiement n'a pas été lié entre-temps
        if self.advance_payment_id:
            payment = self.advance_payment_id
            if payment.fleet_rent_id:
                errors.append(_(
                    "• Le paiement sélectionné (%s) est déjà lié au contrat %s."
                ) % (payment.name, payment.fleet_rent_id.name))
            if payment.reconciled_invoice_ids:
                errors.append(_(
                    "• Le paiement sélectionné (%s) est lié à des factures."
                ) % payment.name)
            
        if errors:
            raise UserError(
                _("Impossible de créer le contrat :\n\n%s") % '\n'.join(errors)
            )

    def _link_payment_to_contract(self, contract):
        """
        Lie le paiement d'avance au contrat créé et poste un message
        dans le chatter du contrat et de l'opportunité.
        """
        self.ensure_one()
        if not self.advance_payment_id:
            return

        payment = self.advance_payment_id

        if payment.fleet_rent_id:
            raise UserError(_(
                "Le paiement %s est déjà lié au contrat %s."
            ) % (payment.name, payment.fleet_rent_id.name))

        # Lier le paiement au contrat
        payment.write({
            'fleet_rent_id': contract.id,
            'is_rental_advance': True,
        })

        # Message dans le chatter du contrat
        contract.message_post(
            body=_(
                "💰 <b>Paiement d'avance lié au contrat</b><br/>"
                "Référence paiement : <b>%s</b><br/>"
                "Montant : <b>%.2f DH</b><br/>"
                "Date : %s<br/>"
                "%s"
                "%s"
            ) % (
                payment.name or '—',
                payment.amount,
                payment.date.strftime('%d/%m/%Y') if payment.date else '—',
                ("<br/>Réf. : %s" % payment.name) if payment.name else '',
                ("<br/>Observations : %s" % self.advance_notes) if self.advance_notes else '',
            ),
        )

        # Message dans le chatter de l'opportunité
        self.lead_id.message_post(
            body=_(
                "💰 <b>Paiement d'avance lié au contrat %s</b><br/>"
                "Paiement : <b>%s</b> — Montant : %.2f DH — Date : %s<br/>"
                "Total contrat HT : %.2f DH | TTC : %.2f DH"
            ) % (
                contract.name,
                payment.name or '—',
                payment.amount,
                payment.date.strftime('%d/%m/%Y') if payment.date else '—',
                self.estimated_total_ht,
                self.estimated_total_ttc,
            ),
        )

        _logger.info(
            "Paiement #%s (%.2f DH) lié au contrat #%s depuis l'opportunité #%s",
            payment.id, payment.amount, contract.id, self.lead_id.id,
        )

    # ─── ACTIONS ──────────────────────────────────────────────────────────────

    def action_confirm_conversion(self):
        """
        Étape finale — Confirme la conversion d'un DEVIS APPROUVÉ :
          1. Valide les pré-requis (dont approval_status='approved')
          2. Crée le contrat de location
          3. Lie le paiement d'avance au contrat (si présent)
          4. Met à jour le lead et le devis source
          5. Redirige vers la fiche du contrat
        """
        self.ensure_one()

        # ── 1. Validation ─────────────────────────────────────────────────────
        self._validate_before_conversion()

        # ── 2. Préparer les données du contrat ────────────────────────────────
        contract_vals = {
            'customer_id':          self.customer_id.id,
            'contract_type':        self.contract_type,
            'rent_start_datetime':  self.rent_start_datetime,
            'rent_end_datetime':    self.rent_end_datetime,
            'daily_rate':           self.unit_price_ht,
            'discount_percent':     self.discount_percent,
            'category_invoiced':    self.vehicle_category_id.id if self.vehicle_category_id else False,
            'rounded':              self.rounded,
            'vat_percent':          self.vat_percent,
            'rental_tariff_id':     self.rental_tariff_id.id if self.rental_tariff_id else False,
            'estimated_total_ht':   self.estimated_total_ht,
            'estimated_total_ttc':  self.estimated_total_ttc,
            'source_quotation_id':  self.source_order_id.id if self.source_order_id else False,
            'advance_payment_id':   self.advance_payment_id.id if self.advance_payment_id else False,
        }

        if self.contract_type == 'short':
            contract_vals['number_of_days'] = self.number_of_days
        else:
            contract_vals['number_of_months'] = self.number_of_months

        # ── 3. Créer le contrat ───────────────────────────────────────────────
        # Utiliser la méthode du devis si disponible, sinon celle du lead
        if self.source_order_id:
            contract = self.source_order_id._do_convert_to_contract(
                contract_vals=contract_vals,
                converted_order_id=self.source_order_id.id,
            )
        else:
            contract = self.lead_id._do_convert_to_contract(
                contract_vals=contract_vals,
                converted_order_id=None,
            )

        # ── 4. Lier le paiement d'avance ──────────────────────────────────────
        if self.advance_payment_id:
            self._link_payment_to_contract(contract)
            
            # Lier également l'avance au devis source
            if self.source_order_id:
                self.source_order_id.write({
                    'advance_payment_id': self.advance_payment_id.id,
                })
                _logger.info(
                    "Avance liée au devis #%s : paiement #%s (%.2f DH)",
                    self.source_order_id.id, self.advance_payment_id.id, self.advance_payment_id.amount
                )

        # ── 5. Message de synthèse dans le contrat ────────────────────────────
        unit_text = "jour" if self.contract_type == 'short' else "mois"
        period_text = (
            f"{self.number_of_days} jours"
            if self.contract_type == 'short'
            else f"{self.number_of_months:.1f} mois"
        )

        advance_info = ""
        if self.advance_payment_id:
            advance_info = _(
                "Avance liée : <b>%s</b> — %.2f DH (du %s)<br/>"
            ) % (
                self.advance_payment_id.name or '—',
                self.advance_payment_id.amount,
                self.advance_payment_id.date.strftime('%d/%m/%Y')
                if self.advance_payment_id.date else '—',
            )
        elif not self.advance_required:
            advance_info = _("<i>Aucune avance requise pour ce type de contrat (longue durée).</i><br/>")

        devis_info = ""
        if self.source_order_id:
            devis_info = _("Devis source : <b>%s</b> (approuvé le %s par %s)<br/>") % (
                self.source_order_id.name,
                self.source_order_id.approval_date.strftime('%d/%m/%Y') if self.source_order_id.approval_date else '—',
                self.source_order_id.approved_by.name if self.source_order_id.approved_by else '—',
            )

        contract.message_post(body=_(
            "📋 <b>Contrat créé depuis un devis approuvé</b><br/>"
            "Opportunité source : <b>%s</b> (Réf : <b>%s</b>)<br/>"
            "%s"
            "Période : %s → %s (%s)<br/>"
            "Tarif : %.2f DH/%s | Remise : %.1f%%<br/>"
            "Total HT : %.2f DH | Total TTC : %.2f DH<br/>"
            "%s"
            "%s"
        ) % (
            self.lead_name,
            self.lead_rental_reference or '—',
            devis_info,
            self.rent_start_datetime.strftime('%d/%m/%Y %H:%M') if self.rent_start_datetime else '—',
            self.rent_end_datetime.strftime('%d/%m/%Y %H:%M') if self.rent_end_datetime else '—',
            period_text,
            self.unit_price_ht,
            unit_text,
            self.discount_percent,
            self.estimated_total_ht,
            self.estimated_total_ttc,
            advance_info,
            (_("<br/>Observations : %s") % self.advance_notes) if self.advance_notes else '',
        ))

        _logger.info(
            "Wizard de conversion : contrat %s créé depuis le devis #%s. "
            "Type: %s | Durée: %s | Total HT: %.2f | Avance: %s",
            contract.name, self.source_order_id.id if self.source_order_id else self.lead_id.id,
            self.contract_type, period_text,
            self.estimated_total_ht,
            self.advance_payment_id.name if self.advance_payment_id else 'Aucune',
        )

        # ── 6. Rediriger vers le contrat créé ────────────────────────────────
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Contrat de location'),
            'res_model': 'car.rental.contract',
            'res_id':    contract.id,
            'view_mode': 'form',
            'target':    'current',
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}