from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    linked_contract = fields.Char(
        string="Contrat lié",
        compute="_compute_linked_contract",
        store=True,
    )

    total_vendor_refunds = fields.Monetary(
        string="Total avoirs",
        currency_field='currency_id',
        compute="_compute_refund_amounts",
        store=True,
    )

    net_amount_after_refunds = fields.Monetary(
        string="Montant net après avoirs",
        currency_field='currency_id',
        compute="_compute_refund_amounts",
        store=True,
    )

    display_amount_total = fields.Monetary(
        string="Montant total",
        currency_field='currency_id',
        compute="_compute_refund_amounts",
        store=True,
    )

    has_vendor_refund = fields.Boolean(
        string="Avoir associé",
        compute="_compute_refund_amounts",
        store=True,
    )

    refund_move_id = fields.Many2one(
        'account.move',
        string="Avoir",
        compute="_compute_refund_amounts",
        store=True,
    )

    refund_numbers = fields.Char(
        string="Numéro avoir",
        compute="_compute_refund_numbers",
        store=True,
    )

    refund_impact_display = fields.Monetary(
        string="Impact avoirs",
        currency_field='currency_id',
        compute="_compute_refund_amounts",
        store=True,
    )

    refund_has_impact = fields.Boolean(
        string="Impact avoir",
        compute="_compute_refund_amounts",
        store=True,
    )

    # =========================================================
    # FIX SMART-BUTTON PAIEMENTS FOURNISSEUR
    # =========================================================

    hide_vendor_payment_links = fields.Boolean(
        string="Masquer liens paiements fournisseur",
        default=False,
        copy=False,
    )
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # UNIQUEMENT FACTURE FOURNISSEUR
            if vals.get('move_type') == 'in_invoice':

                if vals.get('name', '/') in ('/', 'Nouveau'):
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'account.move.vendor.ff'
                    ) or 'FF1'

        moves = super().create(vals_list)
        return moves
    @api.depends(
        'line_ids.matched_debit_ids',
        'line_ids.matched_credit_ids',
        'payment_state',
    )
    def _compute_payment_count(self):
        super()._compute_payment_count()
        for move in self:
            if move.move_type == 'in_invoice':
                move.payment_count = len(move._get_visible_vendor_payments())

    def _get_visible_vendor_payments(self):
        self.ensure_one()

        payments = self.env['account.payment']
        if self.move_type != 'in_invoice':
            return payments

        payable_lines = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable'
        )
        if not payable_lines:
            return payments

        partials = self.env['account.partial.reconcile'].sudo().search([
            '|',
            ('debit_move_id', 'in', payable_lines.ids),
            ('credit_move_id', 'in', payable_lines.ids),
        ])

        payment_moves = self.env['account.move']
        for partial in partials:
            payment_moves |= partial.debit_move_id.move_id
            payment_moves |= partial.credit_move_id.move_id

        payment_moves -= self

        if payment_moves:
            domain = [
                ('move_id', 'in', payment_moves.ids),
                ('partner_type', '=', 'supplier'),
                ('payment_type', '=', 'outbound'),
            ]
            if 'hide_from_vendor_bill_button' in self.env['account.payment']._fields:
                domain.append(('hide_from_vendor_bill_button', '=', False))

            payments = self.env['account.payment'].sudo().search(domain)

        return payments

    def open_payments(self):
        self.ensure_one()

        if self.move_type == 'in_invoice':
            payments = self._get_visible_vendor_payments()
            return {
                'type': 'ir.actions.act_window',
                'name': _('Paiements'),
                'res_model': 'account.payment',
                'view_mode': 'list,form',
                'domain': [('id', 'in', payments.ids)],
                'context': {'create': False},
            }

        return super().open_payments()

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _force_sync_fleet_documents_state(self):
        Document = self.env['fleet.vehicle.document']

        for move in self:
            docs = Document.search([
                '|',
                ('bill_id', '=', move.id),
                ('bill_id', '=', move.reversed_entry_id.id if move.reversed_entry_id else 0),
            ])

            if docs:
                docs._sync_state_with_bill()

                vehicles = docs.mapped('vehicle_id')
                if vehicles:
                    vehicles._update_vehicle_state_by_rules()
    def _sanitize_write_vals(self, vals):
        vals = dict(vals or {})
        if vals.get('tax_totals') is False:
            vals.pop('tax_totals', None)
        return vals

    def _get_related_vehicle_purchase_orders(self):
        self.ensure_one()

        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id').filtered(
            lambda o: o.vehicle_id
        )
        if purchase_orders:
            return purchase_orders

        if self.invoice_origin:
            names = [name.strip() for name in self.invoice_origin.split(',') if name.strip()]
            if names:
                purchase_orders = self.env['purchase.order'].search([
                    ('name', 'in', names),
                    ('vehicle_id', '!=', False),
                ])
                if purchase_orders:
                    return purchase_orders

        return self.env['purchase.order']

    def _get_sale_order_from_invoice(self):
        self.ensure_one()

        sale_orders = self.invoice_line_ids.mapped('sale_line_ids.order_id')
        if sale_orders:
            return sale_orders[:1]

        if self.invoice_origin:
            names = [name.strip() for name in self.invoice_origin.split(',') if name.strip()]
            if names:
                sale = self.env['sale.order'].search([
                    ('name', 'in', names)
                ], limit=1)
                if sale:
                    return sale

        return False

    def _get_related_expense_purchase_orders(self):
        self.ensure_one()

        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id').filtered(
            lambda o: o and o.vehicle_purchase_type == 'expense'
        )
        if purchase_orders:
            return purchase_orders

        if self.invoice_origin:
            names = [name.strip() for name in self.invoice_origin.split(',') if name.strip()]
            if names:
                purchase_orders = self.env['purchase.order'].search([
                    ('name', 'in', names),
                    ('vehicle_purchase_type', '=', 'expense'),
                ])
                if purchase_orders:
                    return purchase_orders

        return self.env['purchase.order']

    def _get_documents_linked_to_bill(self):
        self.ensure_one()
        return self.env['fleet.vehicle.document'].search([
            ('bill_id', '=', self.id)
        ])

    def _get_documents_linked_to_reversed_bill(self):
        self.ensure_one()
        if not self.reversed_entry_id:
            return self.env['fleet.vehicle.document']
        return self.env['fleet.vehicle.document'].search([
            ('bill_id', '=', self.reversed_entry_id.id)
        ])

    def _get_posted_vendor_refunds(self):
        self.ensure_one()
        return self.reversal_move_ids.filtered(
            lambda r: r.move_type == 'in_refund' and r.state == 'posted'
        )

    def _get_total_posted_vendor_refunds_amount(self):
        self.ensure_one()
        return abs(sum(self._get_posted_vendor_refunds().mapped('amount_total')))

    def _get_net_amount_after_refunds(self):
        self.ensure_one()
        if self.move_type != 'in_invoice':
            return self.amount_total
        return max(self.amount_total - self._get_total_posted_vendor_refunds_amount(), 0.0)

    # ---------------------------------------------------------
    # COMPUTES
    # ---------------------------------------------------------

    @api.depends(
    'invoice_origin',
    'ref',
    'invoice_line_ids.purchase_line_id.order_id.name',
    'invoice_line_ids.purchase_line_id.order_id.origin',
    )
    def _compute_linked_contract(self):
        for move in self:
            contract = False

            purchase_orders = move._get_related_vehicle_purchase_orders()

            if purchase_orders:
                contracts = []

                for po in purchase_orders:
                    if po.origin:
                        contracts.append(po.origin)
                    elif po.name:
                        contracts.append(po.name)

                contracts = [c for c in contracts if c]
                contract = ', '.join(sorted(set(contracts))) if contracts else False

            if not contract:
                contract = move.invoice_origin or move.ref or False

            move.linked_contract = contract

    @api.depends(
        'reversal_move_ids.name',
        'reversal_move_ids.state',
        'reversal_move_ids.move_type',
    )
    def _compute_refund_numbers(self):
        for move in self:
            if move.move_type != 'in_invoice':
                move.refund_numbers = False
                continue

            refunds = move.reversal_move_ids.filtered(
                lambda r: r.move_type == 'in_refund' and r.state == 'posted'
            )
            move.refund_numbers = ', '.join(refunds.mapped('name')) if refunds else False

    @api.depends(
        'amount_total',
        'move_type',
        'reversal_move_ids.state',
        'reversal_move_ids.move_type',
        'reversal_move_ids.amount_total',
        'reversal_move_ids.name',
    )
    def _compute_refund_amounts(self):
        for move in self:
            total_refunds = 0.0
            net_amount = move.amount_total
            has_refund = False
            refund_move = False
            refund_impact = 0.0
            refund_has_impact = False

            if move.move_type == 'in_invoice':
                refunds = move.reversal_move_ids.filtered(
                    lambda r: r.move_type == 'in_refund' and r.state == 'posted'
                )
                total_refunds = abs(sum(refunds.mapped('amount_total')))
                net_amount = max(move.amount_total - total_refunds, 0.0)
                has_refund = bool(refunds)
                refund_move = refunds[:1] if refunds else False
                refund_impact = total_refunds
                refund_has_impact = total_refunds > 0

            move.total_vendor_refunds = total_refunds
            move.net_amount_after_refunds = net_amount
            move.display_amount_total = net_amount if move.move_type == 'in_invoice' else move.amount_total
            move.has_vendor_refund = has_refund
            move.refund_move_id = refund_move
            move.refund_impact_display = refund_impact
            move.refund_has_impact = refund_has_impact
    def action_clear_payments_widget(self):
        for move in self:
            if move.move_type != 'in_invoice':
                continue

            for fname in [
                'invoice_payments_widget',
                'invoice_outstanding_credits_debits_widget',
                'payments_widget',
            ]:
                if fname in move._fields:
                    try:
                        move[fname] = False
                    except Exception:
                        pass

            move.invalidate_recordset()
            move.line_ids.invalidate_recordset()

            if hasattr(move, '_compute_amount'):
                move._compute_amount()

            if hasattr(move, '_compute_payment_state'):
                move._compute_payment_state()

        return True
    # ---------------------------------------------------------
    # TRACKING
    # ---------------------------------------------------------

    def _sync_fleet_location_tracking(self):
        tracking = self.env['fleet.location.tracking'].sudo()

        for move in self:
            if move.state != 'posted':
                continue

            # =========================================
            # 🔥 FACTURE CLIENT (LOCATION)
            # =========================================
            if move.move_type == 'out_invoice':
                contract = move.fleet_rent_id if 'fleet_rent_id' in move._fields and move.fleet_rent_id else False

                if not contract:
                    continue

                vehicle = contract.current_vehicle_id

                if not vehicle and contract.contract_vehicle_ids:
                    vehicle = contract.contract_vehicle_ids[:1].vehicle_id

                if not vehicle:
                    continue

                tracking._upsert({
                    'name': move.name or contract.name or _('Facture location'),
                    'vehicle_id': vehicle.id,
                    'nature_operation': 'location',
                    'type_operation': tracking._get_location_type_from_contract(contract),
                    'service_code': False,
                    'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
                    'partner_id': move.partner_id.id if move.partner_id else contract.customer_id.id,
                    'product_id': vehicle.product_id.id if vehicle.product_id else False,
                    'montant_ht': abs(move.amount_untaxed or 0.0),
                    'taxe': abs(move.amount_tax or 0.0),
                    'montant_ttc': abs(move.amount_total or 0.0),
                    'sale_order_id': contract.source_quotation_id.id if contract.source_quotation_id else False,
                    'bill_id': move.id,
                    'invoice_reference': move.name or move.ref or False,
                    'source_model': 'account.move',
                    'source_res_id': move.id,
                    'note': _("Facture client location automatique"),
                })

            # =========================================
            # 🔥 FACTURE FOURNISSEUR
            # =========================================
            elif move.move_type == 'in_invoice':
                purchase_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id')

                if not purchase_orders and move.invoice_origin:
                    names = [name.strip() for name in move.invoice_origin.split(',') if name.strip()]
                    purchase_orders = self.env['purchase.order'].search([
                        ('name', 'in', names),
                    ])

                for po in purchase_orders:
                    if po.vehicle_purchase_type == 'contract':
                        tracking.sync_from_purchase_contract_order(po, bill=move)

                    elif po.vehicle_purchase_type == 'expense':
                        tracking.sync_from_expense_purchase_order(po, bill=move)

                    elif po.vehicle_purchase_type == 'leasing_contract':
                        if po.is_leasing_bill_order:
                            continue

                        for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                            tracking.sync_from_purchase_contract_bill_line(line)

                    else:
                        for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                            tracking.sync_from_purchase_contract_bill_line(line)

            # =========================================
            # 🔥 AVOIR FOURNISSEUR
            # =========================================
            elif move.move_type == 'in_refund':
                for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                    tracking.sync_from_vendor_refund_line(line)

            # =========================================
            # 🔥 AVOIR CLIENT (LOCATION)
            # =========================================
            elif move.move_type == 'out_refund':
                contract = False

                if 'fleet_rent_id' in move._fields and move.fleet_rent_id:
                    contract = move.fleet_rent_id
                elif move.reversed_entry_id and 'fleet_rent_id' in move.reversed_entry_id._fields:
                    contract = move.reversed_entry_id.fleet_rent_id

                if not contract:
                    continue

                vehicle = contract.current_vehicle_id

                if not vehicle and contract.contract_vehicle_ids:
                    vehicle = contract.contract_vehicle_ids[:1].vehicle_id

                if not vehicle:
                    continue

                tracking._upsert({
                    'name': move.name or _('Avoir client location'),
                    'vehicle_id': vehicle.id,
                    'nature_operation': 'location',
                    'type_operation': tracking._get_location_type_from_contract(contract),
                    'service_code': False,
                    'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
                    'partner_id': move.partner_id.id if move.partner_id else contract.customer_id.id,
                    'product_id': vehicle.product_id.id if vehicle.product_id else False,
                    'montant_ht': -abs(move.amount_untaxed or 0.0),
                    'taxe': -abs(move.amount_tax or 0.0),
                    'montant_ttc': -abs(move.amount_total or 0.0),
                    'sale_order_id': contract.source_quotation_id.id if contract.source_quotation_id else False,
                    'bill_id': move.id,
                    'original_bill_id': move.reversed_entry_id.id if move.reversed_entry_id else False,
                    'invoice_reference': move.name or move.ref or False,
                    'source_model': 'account.move',
                    'source_res_id': move.id,
                    'note': _("Avoir client location automatique"),
                })
    # ---------------------------------------------------------
    # DOCUMENTS VEHICULE
    # ---------------------------------------------------------

    def _sync_fleet_vehicle_documents(self):
        PurchaseOrder = self.env['purchase.order']
        Document = self.env['fleet.vehicle.document']

        expense_orders = self.env['purchase.order']
        documents = self.env['fleet.vehicle.document']

        for move in self.filtered(lambda m: m.move_type in ('in_invoice', 'in_refund')):
            linked_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id').filtered(
                lambda o: o.vehicle_purchase_type == 'expense'
            )
            expense_orders |= linked_orders

            if not linked_orders and move.invoice_origin:
                names = [name.strip() for name in move.invoice_origin.split(',') if name.strip()]
                if names:
                    expense_orders |= PurchaseOrder.search([
                        ('name', 'in', names),
                        ('vehicle_purchase_type', '=', 'expense'),
                    ])

            documents |= Document.search([('bill_id', '=', move.id)])

            if move.move_type == 'in_refund' and move.reversed_entry_id:
                documents |= Document.search([('bill_id', '=', move.reversed_entry_id.id)])

        for order in expense_orders:
            order._sync_related_documents_with_purchase()

        for doc in documents:
            bill = doc.bill_id
            if bill and bill.move_type == 'in_invoice':
                vals = {}

                if 'amount' in doc._fields:
                    vals['amount'] = bill._get_net_amount_after_refunds()

                if vals:
                    doc.write(vals)

                if hasattr(doc, '_sync_state_with_bill'):
                    doc._sync_state_with_bill()

    def _handle_vendor_refund_vehicle_documents(self):
        Document = self.env['fleet.vehicle.document']
        documents_to_update = Document

        refund_moves = self.filtered(
            lambda m: m.move_type == 'in_refund' and m.state == 'posted' and m.reversed_entry_id
        )

        for refund in refund_moves:
            original_bill = refund.reversed_entry_id
            documents = Document.search([('bill_id', '=', original_bill.id)])

            refunded_amount = original_bill._get_total_posted_vendor_refunds_amount()
            original_amount = original_bill.amount_total
            is_full_refund = refunded_amount >= original_amount

            for doc in documents:
                vals = {}

                if 'amount' in doc._fields:
                    vals['amount'] = original_bill._get_net_amount_after_refunds()

                if is_full_refund:
                    if 'state' in doc._fields:
                        selection = getattr(doc._fields['state'], 'selection', False) or []
                        selection_keys = [key for key, _label in selection]

                        if 'draft' in selection_keys:
                            vals['state'] = 'draft'
                        elif 'not_paid' in selection_keys:
                            vals['state'] = 'not_paid'

                    if 'bill_id' in doc._fields:
                        vals['bill_id'] = False

                if vals:
                    doc.write(vals)

            documents_to_update |= documents

        return documents_to_update

    def _post_process_vehicle_documents_and_tracking(self):
        vendor_moves = self.filtered(lambda m: m.move_type in ('in_invoice', 'in_refund'))

        if vendor_moves:
            vendor_moves._sync_fleet_vehicle_documents()

        all_trackable = self.filtered(
            lambda m: m.move_type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund')
        )

        if all_trackable:
            all_trackable._sync_fleet_location_tracking()

        if vendor_moves:
            refunded_documents = vendor_moves._handle_vendor_refund_vehicle_documents()
            if refunded_documents:
                expense_orders = refunded_documents.mapped('purchase_order_id')
                for order in expense_orders:
                    if order:
                        order._sync_related_documents_with_purchase()

        # Génération du plan véhicule uniquement pour contrat achat/leasing
        # Jamais pour les dépenses documents : assurance, vignette, carte grise, permis...
        for move in vendor_moves:
            if move.move_type == 'in_invoice' and move.state == 'posted':
                purchase_orders = move._get_related_vehicle_purchase_orders()

                for order in purchase_orders:
                    if not order.vehicle_id:
                        continue

                    if (
                        order.vehicle_purchase_type in ('contract', 'leasing_contract')
                        and not order.is_leasing_bill_order
                    ):
                        order.vehicle_id._generate_paid_vehicle_documents_plan(
                            purchase_order=order,
                            bill=move
                        )

                    order.vehicle_id._update_vehicle_state_by_rules()

                documents = move._get_documents_linked_to_bill()
                if documents:
                    for doc in documents:
                        if hasattr(doc, '_sync_state_with_bill'):
                            doc._sync_state_with_bill()

            elif (
                move.move_type == 'in_refund'
                and move.state == 'posted'
                and move.reversed_entry_id
            ):
                original_bill = move.reversed_entry_id
                original_documents = self.env['fleet.vehicle.document'].search([
                    ('bill_id', '=', original_bill.id)
                ])

                if original_documents:
                    for doc in original_documents:
                        if hasattr(doc, '_sync_state_with_bill'):
                            doc._sync_state_with_bill()

    # ---------------------------------------------------------
    # ORM
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        return moves

    def action_post(self):
        res = super().action_post()

        # =====================================================
        # EXISTANT : tracking + documents
        # =====================================================
        self._sync_fleet_location_tracking()
        self._sync_fleet_vehicle_documents()

        # =====================================================
        # VENTE VEHICULE : tracking + statut Cession
        # =====================================================
        Tracking = self.env['fleet.location.tracking'].sudo()
        VehicleState = self.env['fleet.vehicle.state'].sudo()

        cession_state = VehicleState.search([
            ('name', '=', 'Cession')
        ], limit=1)

        for move in self:
            if move.move_type != 'out_invoice' or move.state != 'posted':
                continue

            sale_orders = self.env['sale.order']

            if move.invoice_origin:
                names = [n.strip() for n in move.invoice_origin.split(',') if n.strip()]
                sale_orders = self.env['sale.order'].sudo().search([
                    ('name', 'in', names),
                    ('vehicle_id', '!=', False),
                ])

            if not sale_orders:
                sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id').filtered(
                    lambda s: s.vehicle_id
                )

            for sale in sale_orders:
                vehicle = sale.vehicle_id
                if not vehicle:
                    continue

                Tracking._upsert({
                    'name': move.name or sale.name or _('Vente véhicule'),
                    'vehicle_id': vehicle.id,
                    'nature_operation': 'cession',
                    'type_operation': 'vente',
                    'service_code': False,
                    'date_operation': move.invoice_date or move.date or fields.Date.context_today(self),
                    'partner_id': move.partner_id.id if move.partner_id else sale.partner_id.id,
                    'product_id': vehicle.product_id.id if vehicle.product_id else False,
                    'montant_ht': abs(move.amount_untaxed or 0.0),
                    'taxe': abs(move.amount_tax or 0.0),
                    'montant_ttc': abs(move.amount_total or 0.0),
                    'sale_order_id': sale.id,
                    'bill_id': move.id,
                    'invoice_reference': move.name or move.ref or False,
                    'source_model': 'account.move',
                    'source_res_id': move.id,
                    'note': _("Vente véhicule / Cession automatique"),
                })

                if cession_state:
                    vehicle.sudo().write({
                        'state_id': cession_state.id
                    })

                sale.message_post(body=_(
                    "✅ Véhicule <b>%s</b> passé automatiquement en état <b>Cession</b> "
                    "après validation de la facture <b>%s</b>."
                ) % (vehicle.display_name, move.name))

        return res
    def write(self, vals):
        vals = self._sanitize_write_vals(vals)

        res = super().write(vals)

        # Ne pas bloquer/modifier les factures brouillon pendant l'édition
        posted_moves = self.filtered(lambda m: m.state == 'posted')

        if not posted_moves:
            return res

        # Synchro uniquement après validation / paiement / avoir
        tracked_fields = {
            'payment_state',
            'state',
            'reversed_entry_id',
        }

        need_post_process = bool(tracked_fields.intersection(vals.keys()))

        if 'payment_state' in vals:
            posted_moves._force_sync_fleet_documents_state()

        if need_post_process:
            posted_moves._post_process_vehicle_documents_and_tracking()
            posted_moves._force_sync_fleet_documents_state()

        for move in posted_moves:
            if move.move_type == 'out_invoice':
                sale_orders = self.env['sale.order'].search([
                    ('name', '=', move.invoice_origin),
                    ('vehicle_id', '!=', False),
                ])

                if not sale_orders:
                    sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id').filtered(
                        lambda s: s.vehicle_id
                    )

                for sale in sale_orders:
                    if sale.vehicle_id:
                        sale.vehicle_id._update_vehicle_state_by_rules()

        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    display_price_subtotal_net = fields.Monetary(
        string="Montant net",
        currency_field='currency_id',
        compute='_compute_display_price_subtotal_net',
        store=False,
    )

    @api.depends(
        'price_subtotal',
        'move_id.move_type',
        'move_id.net_amount_after_refunds',
        'move_id.amount_untaxed',
        'display_type',
    )
    def _compute_display_price_subtotal_net(self):
        for line in self:
            if line.display_type or not line.move_id or line.move_id.move_type != 'in_invoice':
                line.display_price_subtotal_net = line.price_subtotal
                continue

            move = line.move_id
            untaxed = move.amount_untaxed or 0.0
            net_total = move.net_amount_after_refunds or move.amount_total or 0.0

            real_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            if len(real_lines) == 1:
                line.display_price_subtotal_net = net_total
                continue

            if untaxed:
                ratio = line.price_subtotal / untaxed
                line.display_price_subtotal_net = net_total * ratio
            else:
                line.display_price_subtotal_net = line.price_subtotal