from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FleetVehicleDocument(models.Model):
    _name = 'fleet.vehicle.document'
    _description = 'Document Administratif Véhicule'
    _rec_name = 'name'
    _order = 'date_start desc, id desc'

    _sql_constraints = [
        ('supplier_reference_unique', 'unique(supplier_reference)', 'La référence fournisseur doit être unique.'),
    ]

    name = fields.Char(string="Nom", required=True, copy=False, default=lambda self: _('Nouveau'))
    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule", required=True)

    document_year = fields.Integer(
        string="Année",
        compute="_compute_document_year",
        store=True,
        index=True
    )

    numero_w = fields.Char(
        string="Numéro W",
        related="vehicle_id.numero_w",
        store=True,
        readonly=True
    )

    license_plate = fields.Char(
        string="Immatriculation",
        related="vehicle_id.license_plate",
        store=True,
        readonly=True
    )

    vehicle_display = fields.Char(
        string="Véhicule",
        compute="_compute_vehicle_display",
        store=True
    )

    type_acquisition = fields.Selection(
        related="vehicle_id.type_acquisition",
        string="Type d'acquisition",
        store=True,
        readonly=True
    )

    model_name = fields.Char(
        string="Modèle",
        related="vehicle_id.model_name",
        store=True,
        readonly=True
    )

    brand_name = fields.Char(
        string="Marque",
        related="vehicle_id.brand_name",
        store=True,
        readonly=True
    )

    category_id = fields.Many2one(
        'fleet.vehicle.model.category',
        string="Catégorie",
        related="vehicle_id.category_id",
        store=True,
        readonly=True
    )
    assurance_attestation_number = fields.Char(string="N° attestation")
    assurance_policy_number = fields.Char(string="Numéro police")
    assurance_type_text = fields.Char(string="Type assurance")

    vignette_number = fields.Char(string="Numéro vignette")

    visite_number = fields.Char(string="Numéro visite technique")
    visite_type = fields.Char(string="Type visite technique")
    visite_center = fields.Char(string="Centre de visite technique")
    vin_sn = fields.Char(
        string="N° de châssis",
        related="vehicle_id.vin_sn",
        store=True,
        readonly=True
    )

    document_type = fields.Selection([
        ('carte_grise', 'Carte grise'),
        ('permis_circulation', 'Permis de circulation'),
        ('vignette', 'Vignette'),
        ('assurance', 'Assurance'),
        ('visite', 'Visite technique'),
        ('immatriculation', 'Frais immatriculation'),
        ('jawaz', 'Jawaz'),
        ('carburant', 'Carburant'),
        ('carte_verte', 'Carte verte'),
    ], string="Type", required=True)

    supplier_reference = fields.Char(
        string="Référence fournisseur",
        readonly=True,
        copy=False,
        index=True,
        default=False,
    )

    supplier_id = fields.Many2one('res.partner', string="Fournisseur")
    date_start = fields.Date(string="Date début")
    date_end = fields.Date(string="Date fin")
    amount = fields.Float(string="Montant par véhicule")

    invoice_number = fields.Char(string="Numéro de facture", copy=False)

    insurance_type = fields.Selection([
        ('rc', 'RC'),
        ('tout_risque', 'Tout risque'),
    ], string="Type assurance")

    state = fields.Selection([
        ('not_paid', 'Non payé'),
        ('purchase_created', 'Bon de commande créé'),
        ('billed', 'Facturé'),
        ('paid', 'Payé'),
        ('avoirise', 'Avoirisé'),
        ('expired', 'Expiré'),
    ], string="Statut", default='not_paid')

    has_status = fields.Boolean(
        string="A un statut",
        compute="_compute_has_status",
        store=True
    )

    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        readonly=True,
        copy=False
    )

    source_purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Contrat / achat source",
        readonly=True,
        copy=False
    )

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="BL document",
        readonly=True,
        copy=False
    )

    bill_id = fields.Many2one(
        'account.move',
        string="Facture fournisseur",
        readonly=True,
        copy=False
    )

    notes = fields.Text(string="Commentaire")

    attachment = fields.Binary(string="Pièce jointe")
    attachment_filename = fields.Char(string="Nom fichier")

    auto_generated = fields.Boolean(
        string="Généré automatiquement",
        default=False,
        copy=False
    )

    monthly_detail_ids = fields.One2many(
        'fleet.vehicle.document.monthly.detail',
        'document_id',
        string="Détails mensuels",
        copy=False
    )

    monthly_total = fields.Float(
        string="Total mensuel",
        compute="_compute_monthly_total",
        store=True
    )

    @api.depends('date_start')
    def _compute_document_year(self):
        for rec in self:
            rec.document_year = rec.date_start.year if rec.date_start else False

    @api.depends('document_type')
    def _compute_has_status(self):
        for rec in self:
            rec.has_status = True

    @api.depends('monthly_detail_ids.amount')
    def _compute_monthly_total(self):
        for rec in self:
            rec.monthly_total = sum(rec.monthly_detail_ids.mapped('amount'))

    @api.depends('license_plate', 'numero_w')
    def _compute_vehicle_display(self):
        for rec in self:
            rec.vehicle_display = f"{rec.license_plate or ''} / {rec.numero_w or ''}"

    @api.onchange('document_type', 'vehicle_id')
    def _onchange_name(self):
        for rec in self:
            if rec.document_type and rec.vehicle_id:
                type_label = dict(self._fields['document_type'].selection).get(rec.document_type)
                rec.name = f"{type_label} - {rec.vehicle_id.display_name}"
            elif rec.document_type:
                rec.name = dict(self._fields['document_type'].selection).get(rec.document_type)

    @api.onchange('document_type')
    def _onchange_document_type_status(self):
        for rec in self:
            if not rec.state:
                rec.state = 'not_paid'

            if rec.document_type != 'assurance':
                rec.insurance_type = False

    @api.onchange('bill_id')
    def _onchange_bill_id(self):
        for rec in self:
            if rec.bill_id:
                rec.invoice_number = rec.bill_id.ref or rec.bill_id.name or False

    def _get_related_vendor_credit_note(self):
        self.ensure_one()

        if not self.bill_id:
            return self.env['account.move']

        return self.env['account.move'].search([
            ('move_type', '=', 'in_refund'),
            ('reversed_entry_id', '=', self.bill_id.id),
            ('state', '!=', 'cancel'),
        ], order='id desc', limit=1)

    def _sync_state_with_bill(self):
        today = fields.Date.context_today(self)

        for rec in self:
            if not rec.has_status:
                continue

            updates = {}
            new_state = rec.state

            credit_note = rec._get_related_vendor_credit_note()

            if rec.bill_id:
                invoice_number = rec.bill_id.ref or rec.bill_id.name or False

                if rec.invoice_number != invoice_number:
                    updates['invoice_number'] = invoice_number

                if credit_note and credit_note.state == 'posted':
                    bill_total = abs(rec.bill_id.amount_total or 0.0)
                    credit_total = abs(credit_note.amount_total or 0.0)

                    if credit_total >= bill_total and bill_total > 0:
                        new_state = 'not_paid'
                        updates.update({
                            'bill_id': False,
                            'invoice_number': False,
                            'supplier_reference': False,
                        })
                    else:
                        new_state = 'avoirise'

                elif rec.bill_id.payment_state == 'paid':
                    new_state = 'paid'

                    if not rec.supplier_reference:
                        updates['supplier_reference'] = rec._generate_unique_supplier_reference()

                elif rec.bill_id.payment_state in ('partial', 'in_payment'):
                    new_state = 'billed'

                else:
                    new_state = 'billed'

            elif rec.purchase_order_id:
                if rec.state not in ('paid', 'avoirise'):
                    new_state = 'purchase_created'

            else:
                if rec.date_end and rec.date_end < today:
                    new_state = 'expired'
                elif rec.state not in ('paid', 'avoirise', 'expired'):
                    new_state = 'not_paid'

            if new_state != rec.state:
                updates['state'] = new_state

            if updates:
                rec.with_context(skip_document_state_sync=True).write(updates)

    def _generate_unique_supplier_reference(self):
        self.ensure_one()

        if self.supplier_reference:
            return self.supplier_reference

        prefix = "DOC-FLT-%s-" % fields.Date.context_today(self).strftime("%Y%m%d")
        number = 1

        while True:
            candidate = f"{prefix}{number:04d}"
            exists = self.search_count([
                ('id', '!=', self.id),
                ('supplier_reference', '=', candidate),
            ])
            if not exists:
                return candidate
            number += 1

    def _get_purchase_service_code(self):
        self.ensure_one()

        mapping = {
            'carte_grise': 'immatriculation',
            'permis_circulation': 'immatriculation',
            'assurance': 'assurance',
            'vignette': 'vignette',
            'visite': 'visite_technique',
            'immatriculation': 'immatriculation',
            'jawaz': 'jawaz',
            'carburant': 'carburant',
            'carte_verte': 'carte_verte',
        }

        return mapping.get(self.document_type)

    def _create_product(self):
        for rec in self:
            if not rec.document_type:
                continue

            product_name = dict(rec._fields['document_type'].selection).get(rec.document_type)
            service_code = rec._get_purchase_service_code()

            product = rec.env['product.product'].search([
                ('name', '=', product_name)
            ], limit=1)

            if product:
                updates = {}

                if service_code:
                    service_type = rec.env['fleet.service.type'].search([
                        ('service_code', '=', service_code)
                    ], limit=1)

                    if service_type and product.product_tmpl_id.fleet_service_type_id != service_type:
                        updates['fleet_service_type_id'] = service_type.id

                if updates:
                    product.product_tmpl_id.write(updates)

                rec.with_context(skip_document_state_sync=True).write({
                    'product_id': product.id
                })
                continue

            vals = {
                'name': product_name,
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': False,
            }

            if service_code:
                service_type = rec.env['fleet.service.type'].search([
                    ('service_code', '=', service_code)
                ], limit=1)

                if service_type:
                    vals['fleet_service_type_id'] = service_type.id

            template = rec.env['product.template'].create(vals)
            product = template.product_variant_id

            rec.with_context(skip_document_state_sync=True).write({
                'product_id': product.id
            })

    def _get_or_create_document_product(self):
        self.ensure_one()

        service_code = self._get_purchase_service_code()
        if not service_code:
            return False

        if self.product_id:
            product_code = self.product_id.product_tmpl_id.fleet_service_type_id.service_code
            if product_code == service_code:
                return self.product_id

        product = self.env['product.product'].search([
            ('purchase_ok', '=', True),
            ('product_tmpl_id.fleet_service_type_id.service_code', '=', service_code),
        ], limit=1)

        if not product:
            self._create_product()
            product = self.product_id

        if not product:
            return False

        product_code = product.product_tmpl_id.fleet_service_type_id.service_code
        if product_code != service_code:
            raise ValidationError(_("Le produit sélectionné n’est pas autorisé pour ce type d’achat."))

        if self.product_id != product:
            self.product_id = product.id

        return product

    def _must_generate_monthly_lines(self):
        self.ensure_one()
        return self.document_type in ('assurance', 'vignette', 'visite')

    def _get_month_starts_between(self, start_date, end_date):
        if not start_date or not end_date or end_date < start_date:
            return []

        current = start_date.replace(day=1)
        last = end_date.replace(day=1)

        months = []
        while current <= last:
            months.append(current)
            current = current + relativedelta(months=1)

        return months

    def _rebuild_monthly_details(self):
        for rec in self:
            rec.monthly_detail_ids.unlink()

            if not rec._must_generate_monthly_lines():
                continue

            if not rec.date_start or not rec.date_end:
                continue

            if rec.date_end < rec.date_start:
                continue

            months = rec._get_month_starts_between(rec.date_start, rec.date_end)
            if not months:
                continue

            nb_months = len(months)
            commands = []

            if rec.amount <= 0:
                for month_start in months:
                    commands.append((0, 0, {
                        'month_date': month_start,
                        'label': month_start.strftime('%m/%Y'),
                        'amount': 0.0,
                    }))
            else:
                monthly_amount = rec.amount / nb_months
                remaining = rec.amount

                for index, month_start in enumerate(months, start=1):
                    amount = monthly_amount

                    if index == nb_months:
                        amount = remaining

                    remaining -= amount

                    commands.append((0, 0, {
                        'month_date': month_start,
                        'label': month_start.strftime('%m/%Y'),
                        'amount': amount,
                    }))

            rec.with_context(skip_document_state_sync=True).write({
                'monthly_detail_ids': commands
            })

    def generate_missing_periodic_lines_after_approval(self):
        for rec in self:
            if rec.auto_generated:
                continue

            if rec.document_type not in ('assurance', 'vignette', 'visite'):
                continue

            if not rec.vehicle_id or not rec.date_start:
                continue

            existing_auto_lines = self.search([
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('document_type', '=', rec.document_type),
                ('auto_generated', '=', True),
            ])

            if existing_auto_lines:
                existing_auto_lines.unlink()

            if rec.document_type in ('assurance', 'vignette'):
                first_end = rec.date_end or (rec.date_start + relativedelta(years=1, days=-1))

                if rec.date_end != first_end:
                    rec.with_context(skip_document_state_sync=True).write({
                        'date_end': first_end
                    })

                previous_end = first_end

                for i in range(1, 5):
                    start = previous_end + relativedelta(days=1)
                    end = start + relativedelta(years=1, days=-1)

                    self.create([{
                        'name': f"{dict(self._fields['document_type'].selection).get(rec.document_type)} année {i + 1} - {rec.vehicle_id.display_name}",
                        'vehicle_id': rec.vehicle_id.id,
                        'document_type': rec.document_type,
                        'supplier_id': rec.supplier_id.id if rec.supplier_id else False,
                        'date_start': start,
                        'date_end': end,
                        'amount': rec.amount or 0.0,
                        'insurance_type': rec.insurance_type if rec.document_type == 'assurance' else False,
                        'state': 'not_paid',
                        'auto_generated': True,
                        'source_purchase_order_id': rec.source_purchase_order_id.id if rec.source_purchase_order_id else False,
                    }])

                    previous_end = end

            elif rec.document_type == 'visite':
                first_end = rec.date_end or (rec.date_start + relativedelta(months=6, days=-1))

                if rec.date_end != first_end:
                    rec.with_context(skip_document_state_sync=True).write({
                        'date_end': first_end
                    })

                previous_end = first_end

                for i in range(1, 10):
                    start = previous_end + relativedelta(days=1)
                    end = start + relativedelta(months=6, days=-1)

                    self.create([{
                        'name': f"Visite technique {i + 1} - {rec.vehicle_id.display_name}",
                        'vehicle_id': rec.vehicle_id.id,
                        'document_type': 'visite',
                        'supplier_id': rec.supplier_id.id if rec.supplier_id else False,
                        'date_start': start,
                        'date_end': end,
                        'amount': rec.amount or 0.0,
                        'state': 'not_paid',
                        'auto_generated': True,
                        'source_purchase_order_id': rec.source_purchase_order_id.id if rec.source_purchase_order_id else False,
                    }])

                    previous_end = end

    @api.constrains('vehicle_id', 'document_type', 'auto_generated')
    def _check_single_manual_periodic_line(self):
        for rec in self:
            if rec.auto_generated:
                continue

            if rec.document_type not in ('assurance', 'vignette', 'visite'):
                continue

            if not rec.vehicle_id:
                continue

            count = self.search_count([
                ('id', '!=', rec.id),
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('document_type', '=', rec.document_type),
                ('auto_generated', '=', False),
            ])

            if count:
                raise ValidationError(_(
                    "Une seule ligne manuelle est autorisée par véhicule pour ce type de document."
                ))

    def _check_vehicle_bill_paid_before_manual_create(self, vals):
        return

    def _prepare_purchase_order_vals_from_document(self):
        self.ensure_one()

        service_code = self._get_purchase_service_code()
        product = self._get_or_create_document_product()

        if not product:
            raise ValidationError(_("Aucun produit d'achat n'est configuré pour ce type de document."))

        if not product.uom_id:
            raise ValidationError(_("Le produit lié n'a pas d'unité de mesure."))

        line_name = self.name or product.display_name

        if self.date_start and self.date_end:
            line_name = "%s - du %s au %s" % (line_name, self.date_start, self.date_end)
        elif self.date_start:
            line_name = "%s - %s" % (line_name, self.date_start)

        vals = {
            'partner_id': self.supplier_id.id,
            'vehicle_id': self.vehicle_id.id,
            'vehicle_purchase_type': 'expense',
            'fleet_purchase_service_code': service_code,
            'fleet_document_id': self.id,
            'service_document_year': self.document_year or fields.Date.context_today(self).year,
            'origin': self.name,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': line_name,
                'product_qty': 1.0,
                'product_uom_id': product.uom_id.id,
                'price_unit': self.amount or 0.0,
                'date_planned': fields.Datetime.now(),
            })],
        }

        if self.document_type == 'assurance':
            vals.update({
                'assurance_date_start': self.date_start,
                'assurance_date_end': self.date_end,
                'assurance_type': dict(self._fields['insurance_type'].selection).get(self.insurance_type) if self.insurance_type else False,
                'assurance_amount': self.amount or 0.0,
            })

        elif self.document_type == 'vignette':
            vals.update({
                'vignette_date_start': self.date_start,
                'vignette_date_end': self.date_end,
                'vignette_amount': self.amount or 0.0,
            })

        elif self.document_type == 'visite':
            vals.update({
                'visite_date_start': self.date_start,
                'visite_date_end': self.date_end,
                'visite_amount': self.amount or 0.0,
            })

        elif self.document_type in ('carte_grise', 'permis_circulation', 'immatriculation'):
            vals.update({
                'immatriculation_amount': self.amount or 0.0,
            })

        elif self.document_type == 'jawaz':
            vals.update({
                'jawaz_date_start': self.date_start,
                'jawaz_date_end': self.date_end,
            })

        elif self.document_type == 'carburant':
            vals.update({
                'carburant_date_start': self.date_start,
                'carburant_date_end': self.date_end,
            })

        elif self.document_type == 'carte_verte':
            vals.update({
                'carte_verte_date_start': self.date_start,
                'carte_verte_date_end': self.date_end,
            })

        return vals

    def _create_service_vehicle_line_for_po(self, po):
        self.ensure_one()

        service_code = self._get_purchase_service_code()
        if not service_code:
            return False

        line_vals = {
            'purchase_order_id': po.id,
            'service_code': service_code,
            'vehicle_id': self.vehicle_id.id,
            'amount': self.amount or 0.0,
            'note': self.name,
        }

        if 'document_id' in self.env['purchase.order.service.vehicle']._fields:
            line_vals['document_id'] = self.id

        return self.env['purchase.order.service.vehicle'].create(line_vals)

    def action_create_purchase_order_from_document(self):
        self.ensure_one()

        if self.purchase_order_id:
            return self.action_view_purchase_order()

        if not self.vehicle_id:
            raise ValidationError(_("Le véhicule est obligatoire."))

        if not self.supplier_id:
            raise ValidationError(_("Le fournisseur est obligatoire pour créer le bon de commande."))

        if not self.date_start:
            raise ValidationError(_("La date début est obligatoire."))

        if self.document_type not in ('permis_circulation', 'carte_grise'):
            if not self.date_end:
                raise ValidationError(_("La date fin est obligatoire."))

            if self.date_end < self.date_start:
                raise ValidationError(_("La date fin ne peut pas être inférieure à la date début."))

        if self.date_end < self.date_start:
            raise ValidationError(_("La date fin ne peut pas être inférieure à la date début."))

        service_code = self._get_purchase_service_code()
        if not service_code:
            raise ValidationError(_("Ce type de document ne permet pas de créer un bon de commande."))

        po = self.env['purchase.order'].create(
            self._prepare_purchase_order_vals_from_document()
        )

        self._create_service_vehicle_line_for_po(po)

        if hasattr(po, '_sync_vignette_visite_amounts_from_lines'):
            po._sync_vignette_visite_amounts_from_lines()

        if hasattr(po, '_sync_expense_order_line_from_services'):
            po._sync_expense_order_line_from_services()

        if hasattr(po, '_sync_related_documents_with_purchase'):
            po._sync_related_documents_with_purchase()

        vals = {'purchase_order_id': po.id}

        if self.has_status:
            vals['state'] = 'purchase_created'

        self.with_context(skip_document_state_sync=True).write(vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de commande'),
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_purchase_order(self):
        return self.action_create_purchase_order_from_document()

    def action_create_purchase_orders_multi(self):
        docs = self.filtered(lambda r: (
            r.document_type in ('assurance', 'vignette', 'visite')
            and not r.purchase_order_id
        ))

        if not docs:
            raise ValidationError(_("Aucun document sélectionné ne peut créer un BL."))

        suppliers = docs.mapped('supplier_id')
        if len(suppliers) != 1:
            raise ValidationError(_("Veuillez sélectionner des documents avec le même fournisseur."))

        service_codes = docs.mapped(lambda r: r._get_purchase_service_code())
        service_codes = list(set(service_codes))
        if len(service_codes) != 1:
            raise ValidationError(_("Veuillez sélectionner un seul type de document à la fois : assurance, vignette ou visite technique."))

        first = docs[0]
        order_lines = []

        for rec in docs:
            if not rec.vehicle_id:
                raise ValidationError(_("%s : véhicule manquant.") % rec.display_name)

            if not rec.supplier_id:
                raise ValidationError(_("%s : fournisseur manquant.") % rec.display_name)

            if not rec.date_start:
                raise ValidationError(_("%s : date début manquante.") % rec.display_name)

            if rec.document_type not in ('permis_circulation', 'carte_grise'):
                if not rec.date_end:
                    raise ValidationError(_("%s : date fin manquante.") % rec.display_name)

                if rec.date_end < rec.date_start:
                    raise ValidationError(_("%s : date fin inférieure à date début.") % rec.display_name)

            product = rec._get_or_create_document_product()
            if not product or not product.uom_id:
                raise ValidationError(_("%s : produit ou unité de mesure manquant.") % rec.display_name)

            line_name = rec.name or product.display_name
            line_name = "%s - %s - du %s au %s" % (
                line_name,
                rec.license_plate or rec.vehicle_id.display_name,
                rec.date_start,
                rec.date_end
            )

            order_lines.append((0, 0, {
                'product_id': product.id,
                'name': line_name,
                'product_qty': 1.0,
                'product_uom_id': product.uom_id.id,
                'price_unit': rec.amount or 0.0,
                'date_planned': fields.Datetime.now(),
            }))

        po_vals = {
            'partner_id': first.supplier_id.id,
            'vehicle_id': first.vehicle_id.id,
            'vehicle_purchase_type': 'expense',
            'fleet_purchase_service_code': first._get_purchase_service_code(),
            'service_document_year': first.document_year or fields.Date.context_today(self).year,
            'origin': ", ".join(docs.mapped('name')),
            'order_line': order_lines,
        }

        if first.document_type == 'assurance':
            po_vals.update({
                'assurance_date_start': min(docs.mapped('date_start')),
                'assurance_date_end': max(docs.mapped('date_end')),
                'assurance_amount': sum(docs.mapped('amount')),
                'assurance_type': dict(first._fields['insurance_type'].selection).get(first.insurance_type) if first.insurance_type else False,
            })

        elif first.document_type == 'vignette':
            po_vals.update({
                'vignette_date_start': min(docs.mapped('date_start')),
                'vignette_date_end': max(docs.mapped('date_end')),
                'vignette_amount': sum(docs.mapped('amount')),
            })

        elif first.document_type == 'visite':
            po_vals.update({
                'visite_date_start': min(docs.mapped('date_start')),
                'visite_date_end': max(docs.mapped('date_end')),
                'visite_amount': sum(docs.mapped('amount')),
            })

        po = self.env['purchase.order'].create(po_vals)

        for rec in docs:
            rec._create_service_vehicle_line_for_po(po)

            vals = {'purchase_order_id': po.id}
            if rec.has_status:
                vals['state'] = 'purchase_created'

            rec.with_context(skip_document_state_sync=True).write(vals)

        if hasattr(po, '_sync_vignette_visite_amounts_from_lines'):
            po._sync_vignette_visite_amounts_from_lines()

        if hasattr(po, '_sync_expense_order_line_from_services'):
            po._sync_expense_order_line_from_services()

        if hasattr(po, '_sync_related_documents_with_purchase'):
            po._sync_related_documents_with_purchase()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de commande'),
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def action_view_purchase_order(self):
        self.ensure_one()

        if not self.purchase_order_id:
            raise ValidationError(_("Aucun BL document n'existe encore pour ce document."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de commande'),
            'res_model': 'purchase.order',
            'res_id': self.purchase_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_source_purchase_order(self):
        self.ensure_one()

        if not self.source_purchase_order_id:
            raise ValidationError(_("Aucun contrat / achat source n'existe pour ce document."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrat / achat source'),
            'res_model': 'purchase.order',
            'res_id': self.source_purchase_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_vendor_bill(self):
        self.ensure_one()

        if not self.bill_id:
            raise ValidationError(_("Aucune facture fournisseur disponible."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture fournisseur'),
            'res_model': 'account.move',
            'res_id': self.bill_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_vehicle_bill_paid_before_manual_create(vals)

            if not vals.get('state'):
                vals['state'] = 'not_paid'

            if vals.get('document_type') != 'assurance':
                vals['insurance_type'] = False

            if 'supplier_reference' in vals:
                vals['supplier_reference'] = False

        records = super().create(vals_list)

        for rec in records:
            updates = {}

            if not rec.name or rec.name == _('Nouveau'):
                type_label = dict(rec._fields['document_type'].selection).get(rec.document_type, '')
                vehicle_name = rec.vehicle_id.display_name if rec.vehicle_id else ''
                updates['name'] = f"{type_label} - {vehicle_name}" if vehicle_name else type_label

            if rec.bill_id and not rec.invoice_number:
                updates['invoice_number'] = rec.bill_id.ref or rec.bill_id.name or False

            if updates:
                rec.with_context(skip_document_state_sync=True).write(updates)

            if not rec.product_id and rec.document_type:
                rec._create_product()

        records._rebuild_monthly_details()

        if not self.env.context.get('skip_document_state_sync'):
            records._sync_state_with_bill()

        return records

    def write(self, vals):
        result = super().write(vals)

        for rec in self:
            updates = {}

            if rec.document_type != 'assurance' and rec.insurance_type:
                updates['insurance_type'] = False

            if 'document_type' in vals or 'vehicle_id' in vals:
                type_label = dict(rec._fields['document_type'].selection).get(rec.document_type, '')
                vehicle_name = rec.vehicle_id.display_name if rec.vehicle_id else ''
                updates['name'] = f"{type_label} - {vehicle_name}" if vehicle_name else type_label

            if rec.bill_id:
                invoice_number = rec.bill_id.ref or rec.bill_id.name or False
                if rec.invoice_number != invoice_number:
                    updates['invoice_number'] = invoice_number

            if rec.bill_id and rec.bill_id.payment_state == 'paid' and not rec.supplier_reference:
                updates['supplier_reference'] = rec._generate_unique_supplier_reference()

            if updates:
                super(FleetVehicleDocument, rec.with_context(skip_document_state_sync=True)).write(updates)

            if (
                ('document_type' in vals and rec.document_type)
                or ('product_id' not in vals and not rec.product_id and rec.document_type)
            ):
                rec._create_product()

        if any(k in vals for k in ('document_type', 'date_start', 'date_end', 'amount')):
            self._rebuild_monthly_details()

        if not self.env.context.get('skip_document_state_sync'):
            if any(k in vals for k in ('bill_id', 'purchase_order_id', 'state', 'invoice_number', 'date_end')):
                self._sync_state_with_bill()

        return result

    def action_mark_not_paid(self):
        for rec in self:
            if rec.has_status:
                rec.with_context(skip_document_state_sync=True).write({'state': 'not_paid'})

    def action_mark_purchase_created(self):
        for rec in self:
            if rec.has_status:
                rec.with_context(skip_document_state_sync=True).write({'state': 'purchase_created'})

    def action_mark_billed(self):
        for rec in self:
            if rec.has_status:
                rec.with_context(skip_document_state_sync=True).write({'state': 'billed'})

    def action_mark_paid(self):
        for rec in self:
            if rec.has_status:
                updates = {'state': 'paid'}

                if not rec.supplier_reference:
                    updates['supplier_reference'] = rec._generate_unique_supplier_reference()

                rec.with_context(skip_document_state_sync=True).write(updates)

    def action_mark_expired(self):
        for rec in self:
            if rec.has_status:
                rec.with_context(skip_document_state_sync=True).write({'state': 'expired'})


class FleetVehicleDocumentMonthlyDetail(models.Model):
    _name = 'fleet.vehicle.document.monthly.detail'
    _description = 'Détail mensuel document véhicule'
    _order = 'month_date asc, id asc'

    document_id = fields.Many2one(
        'fleet.vehicle.document',
        string="Document",
        required=True,
        ondelete='cascade'
    )

    month_date = fields.Date(string="Mois", required=True)
    label = fields.Char(string="Libellé", required=True)
    amount = fields.Float(string="Montant", required=True)