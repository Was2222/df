from odoo import api, fields, models, _


class FleetLocationTracking(models.Model):
    _name = 'fleet.location.tracking'
    _description = 'Suivi comptable location flotte'
    _order = 'date_operation desc, id desc'

    name = fields.Char(
        string="Référence",
        required=True,
        default=lambda self: _('Nouveau'),
        copy=False
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        index=True
    )

    invoice_reference = fields.Char(
        string="Référence facture",
        readonly=True
    )

    original_bill_id = fields.Many2one(
        'account.move',
        string="Facture d'origine",
        readonly=True
    )
    numero_w = fields.Char(
        string="Numéro W",
        related="vehicle_id.numero_w",
        store=True,
        readonly=True
    )

    immatriculation = fields.Char(
        string="Immatriculation",
        related="vehicle_id.license_plate",
        store=True,
        readonly=True
    )

    modele = fields.Char(
        string="Modèle",
        related="vehicle_id.model_id.name",
        store=True,
        readonly=True
    )

    marque = fields.Char(
        string="Marque",
        related="vehicle_id.brand_name",
        store=True,
        readonly=True
    )

    vin_sn = fields.Char(
        string="N° de châssis",
        related="vehicle_id.vin_sn",
        store=True,
        readonly=True
    )

    # 🔥 écriture comptable (journal entry)
    move_name = fields.Char(
        string="Écriture comptable",
        related="bill_id.name",
        store=True,
        readonly=True
    )
    nature_operation = fields.Selection([
        ('depense', 'Dépenses'),
        ('leasing', 'Leasing'),
        ('location', 'Location'),
        ('cession', 'Cession'),
        ('autre', 'Autre'),
    ], string="Nature d'opération", required=True, index=True)

    type_operation = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('assurance', 'Assurance'),
        ('vignette', 'Vignette'),
        ('visite_technique', 'Visite technique'),
        ('jawaz', 'Jawaz'),
        ('carburant', 'Carburant'),
        ('carte_verte', 'Carte verte'),
        ('immatriculation', 'Frais immatriculation'),
        ('penalite', 'Pénalités'),
        ('leasing', 'Leasing'),
        ('vente', 'Vente'),
        ('short', 'Courte durée'),
        ('medium', 'Moyenne durée'),
        ('long', 'Longue durée'),
        ('achat_vehicule', 'Achat véhicule'),
        ('permis_circulation', 'Permis de circulation'),
        ('carte_grise', 'Carte grise'),
        ('autre', 'Autre'),
    ], string="Type", required=True, index=True)

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
    ], string="Code service")

    nature_operation_label = fields.Char(
        string="Nature d'opération",
        compute="_compute_safe_labels",
        store=False,
    )

    type_operation_label = fields.Char(
        string="Type",
        compute="_compute_safe_labels",
        store=False,
    )

    service_code_label = fields.Char(
        string="Code service",
        compute="_compute_safe_labels",
        store=False,
    )

    date_operation = fields.Date(
        string="Date d'opération",
        required=True,
        default=fields.Date.context_today
    )

    partner_id = fields.Many2one(
        'res.partner',
        string="Tiers",
        index=True
    )

    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        index=True
    )

    montant_ht = fields.Float(string="Montant HT")
    taxe = fields.Float(string="Taxe")
    montant_ttc = fields.Float(string="Montant TTC")

    display_montant_ht = fields.Float(
        string="Montant HT affiché",
        compute="_compute_display_amounts",
        store=True
    )

    display_taxe = fields.Float(
        string="Taxe affichée",
        compute="_compute_display_amounts",
        store=True
    )

    display_montant_ttc = fields.Float(
        string="Montant TTC affiché",
        compute="_compute_display_amounts",
        store=True
    )

    is_negative_line = fields.Boolean(
        string="Ligne négative",
        compute="_compute_display_amounts",
        store=True
    )

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Bon de commande",
        readonly=True
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Commande vente",
        readonly=True
    )

    bill_id = fields.Many2one(
        'account.move',
        string="Facture / Avoir",
        readonly=True
    )

    document_id = fields.Many2one(
        'fleet.vehicle.document',
        string="Document",
        readonly=True
    )

    source_model = fields.Char(string="Modèle source", readonly=True)
    source_res_id = fields.Integer(string="ID source", readonly=True)

    user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        default=lambda self: self.env.user,
        readonly=True
    )

    date_creation = fields.Datetime(
        string="Date création",
        default=fields.Datetime.now,
        readonly=True
    )
    document_id = fields.Many2one(
        'fleet.vehicle.document',
        string="Document",
        copy=False
    )
    note = fields.Text(string="Commentaire")

    _sql_constraints = [
        (
            'unique_tracking_line',
            'unique(source_model, source_res_id, vehicle_id)',
            'Cette ligne existe déjà dans le suivi.'
        )
    ]
    def action_open_ecriture_comptable(self):
        self.ensure_one()

        if not self.bill_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Écriture comptable',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('move_id', '=', self.bill_id.id)],
            'context': {'create': False, 'edit': False},
        }
    @api.model
    def _selection_label_safe(self, field_name, value):
        if not value:
            return ''

        field = self._fields.get(field_name)
        if not field:
            return str(value)

        selection = dict(field.selection)
        return selection.get(value, str(value))

    @api.depends('nature_operation', 'type_operation', 'service_code')
    def _compute_safe_labels(self):
        for rec in self:
            rec.nature_operation_label = rec._selection_label_safe('nature_operation', rec.nature_operation)
            rec.type_operation_label = rec._selection_label_safe('type_operation', rec.type_operation)
            rec.service_code_label = rec._selection_label_safe('service_code', rec.service_code)

    @api.depends('nature_operation', 'montant_ht', 'taxe', 'montant_ttc')
    def _compute_display_amounts(self):
        negative_natures = ('depense', 'leasing')

        for rec in self:
            is_negative = rec.nature_operation in negative_natures
            rec.is_negative_line = is_negative

            sign = -1 if is_negative else 1
            rec.display_montant_ht = (rec.montant_ht or 0.0) * sign
            rec.display_taxe = (rec.taxe or 0.0) * sign
            rec.display_montant_ttc = (rec.montant_ttc or 0.0) * sign

    @api.model
    def _upsert(self, vals):
        domain = [
            ('source_model', '=', vals.get('source_model')),
            ('source_res_id', '=', vals.get('source_res_id')),
            ('vehicle_id', '=', vals.get('vehicle_id')),
            ('product_id', '=', vals.get('product_id')),
        ]

        existing = self.search(domain, limit=1)

        if existing:
            existing.write(vals)
            return existing

        return self.create(vals)
    @api.model
    def _get_location_type_from_contract(self, contract):
        if not contract:
            return 'vente'

        if contract.contract_type in ('short', 'medium', 'long'):
            return contract.contract_type

        return 'vente'

    @api.model
    def sync_from_rental_contract(self, contract, action='start'):
        if not contract or not contract.current_vehicle_id:
            return False

        vehicle = contract.current_vehicle_id

        if action == 'end':
            source_model = 'car.rental.contract.end'
            date_operation = contract.rent_end_date or fields.Date.context_today(self)
            note = _("Fin contrat location")
            name = "%s - FIN" % (contract.name or _("Contrat location"))
        else:
            source_model = 'car.rental.contract.start'
            date_operation = contract.rent_start_date or fields.Date.context_today(self)
            note = _("Début contrat location")
            name = contract.name or _("Contrat location")

        vals = {
            'name': name,
            'vehicle_id': vehicle.id,
            'nature_operation': 'location',
            'type_operation': self._get_location_type_from_contract(contract),
            'service_code': False,
            'date_operation': date_operation,
            'partner_id': contract.customer_id.id if contract.customer_id else False,
            'product_id': vehicle.product_id.id if vehicle.product_id else False,
            'montant_ht': abs(contract.total_amount_ht or 0.0),
            'taxe': abs((contract.total_amount_ttc or 0.0) - (contract.total_amount_ht or 0.0)),
            'montant_ttc': abs(contract.total_amount_ttc or 0.0),
            'sale_order_id': contract.source_quotation_id.id if hasattr(contract, 'source_quotation_id') and contract.source_quotation_id else False,
            'bill_id': False,
            'invoice_reference': contract.name or False,
            'source_model': source_model,
            'source_res_id': contract.id,
            'note': note,
        }

        return self._upsert(vals)
    @api.model
    def _get_purchase_order_for_move_line(self, line):
        move = line.move_id

        if line.purchase_line_id:
            return line.purchase_line_id.order_id

        if move.invoice_origin:
            po = self.env['purchase.order'].search([
                ('name', '=', move.invoice_origin)
            ], limit=1)
            if po:
                return po

        if move.invoice_origin:
            names = [n.strip() for n in move.invoice_origin.split(',') if n.strip()]
            po = self.env['purchase.order'].search([
                ('name', 'in', names)
            ], limit=1)
            if po:
                return po

        return False

    @api.model
    def _get_nature_from_purchase_order(self, po):
        if not po:
            return 'autre'

        if po.vehicle_purchase_type == 'expense':
            return 'depense'

        if po.vehicle_purchase_type == 'contract':
            return 'depense'

        if po.vehicle_purchase_type == 'leasing_contract':
            return 'leasing'

        return 'autre'

    @api.model
    def _get_type_from_purchase_order(self, po):
        if not po:
            return 'autre'

        if po.vehicle_purchase_type == 'expense':
            return po.fleet_purchase_service_code or 'autre'

        if po.vehicle_purchase_type == 'contract':
            return 'achat_vehicule'

        if po.vehicle_purchase_type == 'leasing_contract':
            return 'leasing'

        return 'autre'

    @api.model
    def sync_from_expense_purchase_order(self, po, bill=False):
        if not po or po.vehicle_purchase_type != 'expense':
            return False

        service_lines = po._get_service_vehicle_lines() if hasattr(po, '_get_service_vehicle_lines') else False
        if not service_lines:
            return False

        created = self.env['fleet.location.tracking']

        if not bill:
            bill = po._get_related_vendor_bills().filtered(
                lambda m: m.move_type == 'in_invoice' and m.state == 'posted'
            )[:1]

        date_operation = fields.Date.context_today(self)
        if bill:
            date_operation = bill.invoice_date or bill.date or date_operation

        invoice_lines = self.env['account.move.line']
        if bill:
            invoice_lines = bill.invoice_line_ids.filtered(lambda l: not l.display_type)

        real_service_lines = service_lines.filtered(lambda l: l.vehicle_id)

        for line in real_service_lines:
            product = False

            if 'product_id' in line._fields and line.product_id:
                product = line.product_id
            else:
                product = po.order_line.filtered(
                    lambda l: not l.display_type and l.product_id
                )[:1].product_id

            amount_ht = 0.0
            taxe = 0.0
            amount_ttc = 0.0

            bill_line = self.env['account.move.line']

            if invoice_lines:
                if product:
                    bill_line = invoice_lines.filtered(lambda l: l.product_id == product)[:1]

                if not bill_line and len(invoice_lines) == 1:
                    bill_line = invoice_lines[:1]

                if bill_line:
                    amount_ht = abs(bill_line.price_subtotal or 0.0)
                    taxe = abs((bill_line.price_total or 0.0) - (bill_line.price_subtotal or 0.0))
                    amount_ttc = abs(bill_line.price_total or 0.0)

            if amount_ht == 0 and bill and real_service_lines:
                count = len(real_service_lines) or 1
                amount_ht = abs((bill.amount_untaxed or 0.0) / count)
                taxe = abs((bill.amount_tax or 0.0) / count)
                amount_ttc = abs((bill.amount_total or 0.0) / count)

            if amount_ht == 0:
                amount_ht = abs(line.amount or 0.0)
                taxe = abs(line.tax_amount or 0.0) if 'tax_amount' in line._fields else 0.0
                amount_ttc = abs(line.amount_ttc or 0.0) if 'amount_ttc' in line._fields else amount_ht + taxe

            write_vals = {}

            if 'amount' in line._fields:
                write_vals['amount'] = amount_ht

            if 'tax_amount' in line._fields:
                write_vals['tax_amount'] = taxe

            if 'amount_ttc' in line._fields:
                write_vals['amount_ttc'] = amount_ttc

            if write_vals:
                line.sudo().write(write_vals)

            document = False
            if 'document_id' in line._fields and line.document_id:
                document = line.document_id

                doc_vals = {}
                if 'amount' in document._fields:
                    doc_vals['amount'] = amount_ht

                if doc_vals:
                    document.sudo().write(doc_vals)

            vals = {
                'name': (bill.name or bill.ref or po.name) if bill else po.name,
                'vehicle_id': line.vehicle_id.id if line.vehicle_id else False,
                'document_id': document.id if document else False,
                'nature_operation': 'depense',
                'type_operation': po.fleet_purchase_service_code or 'autre',
                'service_code': po.fleet_purchase_service_code or False,
                'date_operation': date_operation,
                'partner_id': po.partner_id.id if po.partner_id else False,
                'product_id': product.id if product else False,
                'montant_ht': amount_ht,
                'taxe': taxe,
                'montant_ttc': amount_ttc,
                'purchase_order_id': po.id,
                'bill_id': bill.id if bill else False,
                'invoice_reference': (bill.ref or bill.name) if bill else False,
                'source_model': 'purchase.order.service.vehicle',
                'source_res_id': line.id,
                'note': _("Dépense véhicule comptabilisée"),
            }

            created |= self._upsert(vals)

        return created

    @api.model
    def sync_from_purchase_contract_order(self, po, bill=False):
        if not po or po.vehicle_purchase_type != 'contract' or not po.vehicle_id:
            return False

        line = po.order_line.filtered(lambda l: not l.display_type)[:1]

        vals = {
            'name': (bill.name or bill.ref or po.name) if bill else po.name,
            'vehicle_id': po.vehicle_id.id,
            'nature_operation': 'depense',
            'type_operation': 'achat_vehicule',
            'service_code': False,
            'date_operation': (bill.invoice_date or bill.date) if bill else fields.Date.context_today(self),
            'partner_id': bill.partner_id.id if bill and bill.partner_id else po.partner_id.id,
            'product_id': line.product_id.id if line and line.product_id else po.vehicle_id.product_id.id if po.vehicle_id.product_id else False,
            'montant_ht': abs(bill.amount_untaxed or 0.0) if bill else abs(po.amount_untaxed or 0.0),
            'taxe': abs(bill.amount_tax or 0.0) if bill else abs(po.amount_tax or 0.0),
            'montant_ttc': abs(bill.amount_total or 0.0) if bill else abs(po.amount_total or 0.0),
            'purchase_order_id': po.id,
            'bill_id': bill.id if bill else False,
            'invoice_reference': (bill.ref or bill.name) if bill else False,
            'source_model': 'purchase.order',
            'source_res_id': po.id,
            'note': _("Contrat d'achat véhicule comptabilisé"),
        }

        return self._upsert(vals)

    @api.model
    def sync_from_vendor_bill_line(self, line):
        move = line.move_id

        if not move or move.move_type != 'in_invoice':
            return False

        if move.state != 'posted':
            return False

        po = self._get_purchase_order_for_move_line(line)
        if not po:
            return False

        vehicle = po.vehicle_id
        if not vehicle and hasattr(po, '_get_service_vehicle_lines'):
            service_lines = po._get_service_vehicle_lines()
            vehicle = service_lines[:1].vehicle_id if service_lines else False

        nature_operation = self._get_nature_from_purchase_order(po)
        type_operation = self._get_type_from_purchase_order(po)
        service_code = po.fleet_purchase_service_code if po.vehicle_purchase_type == 'expense' else False

        vals = {
            'name': move.name or move.ref or po.name,
            'vehicle_id': vehicle.id if vehicle else False,
            'nature_operation': nature_operation,
            'type_operation': type_operation,
            'service_code': service_code,
            'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
            'partner_id': move.partner_id.id if move.partner_id else False,
            'product_id': line.product_id.id if line.product_id else False,
            'montant_ht': abs(line.price_subtotal or 0.0),
            'taxe': abs((line.price_total or 0.0) - (line.price_subtotal or 0.0)),
            'montant_ttc': abs(line.price_total or 0.0),
            'purchase_order_id': po.id,
            'bill_id': move.id,
            'invoice_reference': move.ref or move.name or False,
            'source_model': 'account.move.line',
            'source_res_id': line.id,
            'note': _("Facture fournisseur comptabilisée"),
        }

        return self._upsert(vals)

    @api.model
    def sync_from_purchase_contract_bill_line(self, line):
        move = line.move_id

        if not move or move.move_type != 'in_invoice':
            return False

        if move.state != 'posted':
            return False

        po = self._get_purchase_order_for_move_line(line)
        if not po:
            return False

        vehicle = po.vehicle_id
        if not vehicle and hasattr(po, '_get_service_vehicle_lines'):
            service_lines = po._get_service_vehicle_lines()
            vehicle = service_lines[:1].vehicle_id if service_lines else False

        nature_operation = self._get_nature_from_purchase_order(po)
        type_operation = self._get_type_from_purchase_order(po)
        service_code = po.fleet_purchase_service_code if po.vehicle_purchase_type == 'expense' else False

        vals = {
            'name': move.name or move.ref or po.name,
            'vehicle_id': vehicle.id if vehicle else False,
            'nature_operation': nature_operation,
            'type_operation': type_operation,
            'service_code': service_code,
            'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
            'partner_id': move.partner_id.id if move.partner_id else False,
            'product_id': line.product_id.id if line.product_id else False,
            'montant_ht': abs(line.price_subtotal or 0.0),
            'taxe': abs((line.price_total or 0.0) - (line.price_subtotal or 0.0)),
            'montant_ttc': abs(line.price_total or 0.0),
            'purchase_order_id': po.id,
            'bill_id': move.id,
            'invoice_reference': move.ref or move.name or False,
            'source_model': 'account.move.line',
            'source_res_id': line.id,
            'note': _("Facture fournisseur comptabilisée"),
        }

        return self._upsert(vals)

    @api.model
    def sync_from_vendor_refund_line(self, line):
        move = line.move_id
        po = line.purchase_line_id.order_id if line.purchase_line_id else False
        original_bill = move.reversed_entry_id if move else False

        if not move or move.move_type != 'in_refund':
            return False

        if not po and original_bill:
            original_po_lines = original_bill.invoice_line_ids.mapped('purchase_line_id.order_id')
            po = original_po_lines[:1] if original_po_lines else False

            if not po and original_bill.invoice_origin:
                names = [name.strip() for name in original_bill.invoice_origin.split(',') if name.strip()]
                if names:
                    po = self.env['purchase.order'].search([
                        ('name', 'in', names)
                    ], limit=1)

        if not po:
            return False

        vehicle = po.vehicle_id

        if not vehicle and hasattr(po, '_get_service_vehicle_lines'):
            service_lines = po._get_service_vehicle_lines()
            vehicle = service_lines[:1].vehicle_id if service_lines else False

        if not vehicle and original_bill:
            original_po_lines = original_bill.invoice_line_ids.mapped('purchase_line_id.order_id')
            original_po = original_po_lines[:1] if original_po_lines else False

            if original_po:
                vehicle = original_po.vehicle_id
                if not vehicle and hasattr(original_po, '_get_service_vehicle_lines'):
                    service_lines = original_po._get_service_vehicle_lines()
                    vehicle = service_lines[:1].vehicle_id if service_lines else False

        type_operation = self._get_type_from_purchase_order(po)
        service_code = po.fleet_purchase_service_code if po.vehicle_purchase_type == 'expense' else False

        vals = {
            'name': move.name or move.ref or _('Avoir fournisseur'),
            'vehicle_id': vehicle.id if vehicle else False,
            'nature_operation': 'depense',
            'type_operation': type_operation,
            'service_code': service_code,
            'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
            'partner_id': move.partner_id.id if move.partner_id else False,
            'product_id': line.product_id.id if line.product_id else False,
            'montant_ht': -abs(line.price_subtotal or 0.0),
            'taxe': -abs((line.price_total or 0.0) - (line.price_subtotal or 0.0)),
            'montant_ttc': -abs(line.price_total or 0.0),
            'purchase_order_id': po.id if po else False,
            'bill_id': move.id,
            'original_bill_id': original_bill.id if original_bill else False,
            'invoice_reference': move.ref or move.name or False,
            'source_model': 'account.move.line',
            'source_res_id': line.id,
            'note': _("Avoir fournisseur lié à la facture d'origine"),
        }

        return self._upsert(vals)

    @api.model
    def sync_from_customer_invoice_line(self, line, vehicle=False, sale_order=False):
        move = line.move_id

        if not move or move.move_type != 'out_invoice':
            return False

        if move.state != 'posted':
            return False

        if line.display_type:
            return False

        contract = False

        if 'fleet_rent_id' in move._fields and move.fleet_rent_id:
            contract = move.fleet_rent_id

        if contract and not vehicle:
            active_vehicle_lines = contract.contract_vehicle_ids.filtered(
                lambda v: not v.end_datetime
            )

            if active_vehicle_lines:
                vehicle = active_vehicle_lines[:1].vehicle_id
            elif contract.contract_vehicle_ids:
                vehicle = contract.contract_vehicle_ids.sorted(
                    'start_datetime',
                    reverse=True
                )[:1].vehicle_id

            if not vehicle:
                vehicle = contract.current_vehicle_id

        if sale_order and not vehicle and sale_order.vehicle_id:
            vehicle = sale_order.vehicle_id

        if not vehicle:
            return False

        vals = {
            'name': move.name or move.ref or _('Facture client location'),
            'vehicle_id': vehicle.id,
            'nature_operation': 'location',
            'type_operation': self._get_location_type_from_contract(contract),
            'service_code': False,
            'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
            'partner_id': move.partner_id.id if move.partner_id else False,
            'product_id': line.product_id.id if line.product_id else False,
            'montant_ht': abs(line.price_subtotal or 0.0),
            'taxe': abs((line.price_total or 0.0) - (line.price_subtotal or 0.0)),
            'montant_ttc': abs(line.price_total or 0.0),
            'sale_order_id': sale_order.id if sale_order else False,
            'bill_id': move.id,
            'invoice_reference': move.ref or move.name or False,
            'source_model': 'account.move.line',
            'source_res_id': line.id,
            'note': _("Facture client location comptabilisée depuis produit"),
        }

        return self._upsert(vals)
    @api.model
    def sync_from_customer_refund_line(self, line, vehicle=False, sale_order=False):
        move = line.move_id

        if not move or move.move_type != 'out_refund':
            return False

        if move.state != 'posted':
            return False

        if line.display_type:
            return False

        original_invoice = move.reversed_entry_id
        if not original_invoice and 'original_invoice_id' in move._fields:
            original_invoice = move.original_invoice_id

        contract = move.fleet_rent_id if 'fleet_rent_id' in move._fields and move.fleet_rent_id else False
        if not contract and original_invoice and 'fleet_rent_id' in original_invoice._fields:
            contract = original_invoice.fleet_rent_id

        if not vehicle and contract:
            active_vehicle_lines = contract.contract_vehicle_ids.filtered(lambda v: not v.end_datetime)
            if active_vehicle_lines:
                vehicle = active_vehicle_lines[:1].vehicle_id
            elif contract.contract_vehicle_ids:
                vehicle = contract.contract_vehicle_ids.sorted('start_datetime', reverse=True)[:1].vehicle_id
            if not vehicle:
                vehicle = contract.current_vehicle_id

        vals = {
            'name': move.name or move.ref or _('Avoir client'),
            'vehicle_id': vehicle.id if vehicle else False,
            'nature_operation': 'location',
            'type_operation': self._get_location_type_from_contract(contract),
            'service_code': False,
            'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
            'partner_id': move.partner_id.id if move.partner_id else False,
            'product_id': line.product_id.id if line.product_id else False,
            'montant_ht': -abs(line.price_subtotal or 0.0),
            'taxe': -abs((line.price_total or 0.0) - (line.price_subtotal or 0.0)),
            'montant_ttc': -abs(line.price_total or 0.0),
            'sale_order_id': sale_order.id if sale_order else False,
            'bill_id': move.id,
            'original_bill_id': original_invoice.id if original_invoice else False,
            'invoice_reference': move.ref or move.name or False,
            'source_model': 'account.move.line',
            'source_res_id': line.id,
            'note': _("Avoir client sur produit de location"),
        }

        return self._upsert(vals)

    @api.model
    def sync_from_leasing_echeance(self, echeance, bill=False):
        contract = echeance.purchase_order_id

        if not contract or not contract.vehicle_id:
            return False

        vals = {
            'name': echeance.name or contract.name,
            'vehicle_id': contract.vehicle_id.id,
            'nature_operation': 'leasing',
            'type_operation': 'leasing',
            'service_code': False,
            'date_operation': echeance.date_prelevement_reel or echeance.date_echeance or fields.Date.context_today(self),
            'partner_id': contract.leasing_company_id.id if contract.leasing_company_id else contract.partner_id.id if contract.partner_id else False,
            'product_id': False,
            'montant_ht': abs(echeance.amount_ht or 0.0),
            'taxe': abs(echeance.tva_amount or 0.0),
            'montant_ttc': abs(echeance.amount_total or 0.0),
            'purchase_order_id': echeance.bill_purchase_order_id.id if echeance.bill_purchase_order_id else False,
            'bill_id': bill.id if bill else (echeance.vendor_bill_id.id if echeance.vendor_bill_id else False),
            'invoice_reference': bill.ref or bill.name if bill else echeance.vendor_bill_id.ref or echeance.vendor_bill_id.name if echeance.vendor_bill_id else False,
            'source_model': 'leasing.echeance',
            'source_res_id': echeance.id,
            'note': _("Echéance leasing"),
        }

        return self._upsert(vals)

    @api.model
    def sync_from_customer_invoice_move(self, move):
        if not move or move.move_type != 'out_invoice' or move.state != 'posted':
            return False

        contract = move.fleet_rent_id if 'fleet_rent_id' in move._fields and move.fleet_rent_id else False
        if not contract:
            return False

        vehicle = contract.current_vehicle_id
        if not vehicle and contract.contract_vehicle_ids:
            active_vehicle_lines = contract.contract_vehicle_ids.filtered(lambda v: not v.end_datetime)
            if active_vehicle_lines:
                vehicle = active_vehicle_lines[:1].vehicle_id
            else:
                vehicle = contract.contract_vehicle_ids.sorted('start_datetime', reverse=True)[:1].vehicle_id

        if not vehicle:
            return False

        vals = {
            'name': move.name or move.ref or contract.name or _('Facture client location'),
            'vehicle_id': vehicle.id,
            'nature_operation': 'location',
            'type_operation': self._get_location_type_from_contract(contract),
            'service_code': False,
            'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
            'partner_id': move.partner_id.id if move.partner_id else contract.customer_id.id if contract.customer_id else False,
            'product_id': vehicle.product_id.id if vehicle.product_id else False,
            'montant_ht': abs(move.amount_untaxed or 0.0),
            'taxe': abs(move.amount_tax or 0.0),
            'montant_ttc': abs(move.amount_total or 0.0),
            'sale_order_id': contract.source_quotation_id.id if hasattr(contract, 'source_quotation_id') and contract.source_quotation_id else False,
            'bill_id': move.id,
            'invoice_reference': move.ref or move.name or False,
            'source_model': 'account.move',
            'source_res_id': move.id,
            'note': _('Facture client location créée depuis contrat'),
        }

        return self._upsert(vals)

    @api.model
    def fix_all_location_tracking_types(self):
        moves = self.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('fleet_rent_id', '!=', False),
        ])

        updated = self.env['fleet.location.tracking']
        for move in moves:
            rec = self.sync_from_customer_invoice_move(move)
            if rec:
                updated |= rec

        return updated

    @api.model
    def sanitize_existing_selection_values(self):
        records = self.search([
            ('nature_operation', 'not in', ['depense', 'leasing', 'location', 'autre'])
        ])

        for rec in records:
            if rec.nature_operation in ('facture_fournisseur', 'avoir_fournisseur'):
                rec.nature_operation = 'depense'
            elif rec.type_operation == 'vente':
                rec.nature_operation = 'cession'

            elif rec.nature_operation in ('facture_client', 'avoir_client'):
                rec.nature_operation = 'location'
            else:
                rec.nature_operation = 'autre'

        return True
    @api.model
    def run_fix_tracking(self):
        return self.fix_all_location_tracking_types()