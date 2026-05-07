from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    state = fields.Selection(
        selection_add=[
            ('received', 'Reçu'),
            ('partial_used', 'Partiellement utilisé'),
        ],
        ondelete={
            'received': 'set default',
            'partial_used': 'set default',
        }
    )

    source_supplier_payment_id = fields.Many2one(
        'account.payment',
        string="Paiement à annuler",
        copy=False,
        domain="[('partner_type','=','supplier'),"
               "('payment_type','=','outbound'),"
               "('partner_id','=',partner_id),"
               "('company_id','=',company_id),"
               "('state','in',('paid','partial_used'))]"
    )

    vendor_bill_line_ids = fields.One2many(
        'account.payment.vendor.bill.line',
        'payment_id',
        string="Pièces fournisseur liées",
        copy=False,
    )

    selected_bill_count = fields.Integer(
        string="Nombre de pièces sélectionnées",
        compute='_compute_vendor_bill_totals'
    )

    selected_bill_total = fields.Monetary(
        string="Total sélectionné",
        currency_field='currency_id',
        compute='_compute_vendor_bill_totals'
    )

    payment_difference = fields.Monetary(
        string="Montant restant",
        compute="_compute_payment_difference",
        currency_field='currency_id',
    )

    hide_from_vendor_bill_button = fields.Boolean(
        string="Masquer du bouton facture fournisseur",
        default=False,
        copy=False,
    )
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # TOUS les paiements fournisseur
            if vals.get('partner_type') == 'supplier':

                if vals.get('name', 'Nouveau') == 'Nouveau':
                    vals['name'] = self.env['ir.sequence'].next_by_code('account.payment.pf') or 'PF1'

        return super().create(vals_list)
    def _refresh_invoice_payment_info(self, invoices):
        for invoice in invoices:
            invoice.invalidate_recordset()
            invoice.line_ids.invalidate_recordset()

            if hasattr(invoice, '_compute_amount'):
                invoice._compute_amount()

            if hasattr(invoice, '_compute_payment_state'):
                invoice._compute_payment_state()

            # Nettoyage affichage widget paiement
            for fname in [
                'invoice_payments_widget',
                'invoice_outstanding_credits_debits_widget',
                'payments_widget',
            ]:
                if fname in invoice._fields:
                    try:
                        invoice[fname] = False
                    except Exception:
                        pass

            if hasattr(invoice, '_sync_fleet_vehicle_documents'):
                invoice._sync_fleet_vehicle_documents()

            if hasattr(invoice, '_post_process_vehicle_documents_and_tracking'):
                invoice._post_process_vehicle_documents_and_tracking()

    def _get_payment_available_amount(self):
        self.ensure_one()

        if self.state == 'draft' or not self.move_id:
            return abs(self.amount or 0.0)

        payment_lines = self.move_id.line_ids.filtered(
            lambda line: (
                line.account_id.account_type in ('liability_payable', 'asset_receivable')
                and not line.reconciled
            )
        )
        return sum(abs(line.amount_residual or 0.0) for line in payment_lines)

    @api.depends('amount', 'selected_bill_total', 'state', 'move_id.line_ids.amount_residual')
    def _compute_payment_difference(self):
        for rec in self:
            available = rec._get_payment_available_amount()
            rec.payment_difference = max(available - (rec.selected_bill_total or 0.0), 0.0)

    @api.depends(
        'vendor_bill_line_ids.selected',
        'vendor_bill_line_ids.amount_to_pay',
        'vendor_bill_line_ids.amount_processed',
    )
    def _compute_vendor_bill_totals(self):
        for payment in self:
            selected_lines = payment.vendor_bill_line_ids.filtered(
                lambda l: l.selected and l.amount_to_pay > 0
            )
            payment.selected_bill_count = len(selected_lines)

            # IMPORTANT:
            # Sur une ligne déjà traitée, on ne recompte pas l'ancien montant.
            # On compte seulement le supplément à payer.
            total_to_process = 0.0
            for line in selected_lines:
                already = abs(line.amount_processed or 0.0)
                asked = abs(line.amount_to_pay or 0.0)
                total_to_process += max(asked - already, 0.0)

            payment.selected_bill_total = total_to_process

    def _get_moves_domain(self):
        self.ensure_one()

        if self.partner_type != 'supplier' or not self.partner_id or not self.company_id:
            return False

        if self.payment_type == 'outbound':
            return [
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial', 'in_payment']),
                ('partner_id', '=', self.partner_id.id),
                ('company_id', '=', self.company_id.id),
            ]

        if self.payment_type == 'inbound':
            if self.source_supplier_payment_id:
                self.source_supplier_payment_id._ensure_vendor_bill_lines_from_reconciliation()

                invoice_ids = self.source_supplier_payment_id.vendor_bill_line_ids.filtered(
                    lambda l: l.is_processed and l.invoice_id and not l.cancellation_payment_id
                ).mapped('invoice_id').ids

                return [
                    ('id', 'in', invoice_ids),
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'posted'),
                    ('partner_id', '=', self.partner_id.id),
                    ('company_id', '=', self.company_id.id),
                ]

            return [('id', '=', 0)]

        return False

    def _get_available_amount_for_move(self, move):
        self.ensure_one()

        if self.payment_type == 'outbound':
            return abs(move.amount_residual or 0.0)

        if self.payment_type == 'inbound':
            return self._get_paid_amount_by_source_payment(move)

        return 0.0

    def _get_paid_amount_by_source_payment(self, invoice):
        self.ensure_one()

        if not self.source_supplier_payment_id:
            return 0.0

        total = 0.0
        source_payment = self.source_supplier_payment_id
        source_payment._ensure_vendor_bill_lines_from_reconciliation()

        source_lines = source_payment.vendor_bill_line_ids.filtered(
            lambda l: l.invoice_id == invoice and not l.cancellation_payment_id
        )

        if source_lines:
            total = sum(source_lines.mapped('amount_to_pay'))

        if total <= 0 and source_payment.move_id:
            payment_lines = source_payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type in ('liability_payable', 'asset_receivable')
            )

            invoice_lines = invoice.line_ids.filtered(
                lambda line: line.account_id.account_type in ('liability_payable', 'asset_receivable')
            )

            partials = self.env['account.partial.reconcile']
            for p_line in payment_lines:
                partials |= p_line.matched_debit_ids
                partials |= p_line.matched_credit_ids

            for partial in partials:
                if partial.debit_move_id in invoice_lines or partial.credit_move_id in invoice_lines:
                    total += abs(partial.amount or 0.0)

        already_received = sum(
            self.env['account.payment.vendor.bill.line'].search([
                ('invoice_id', '=', invoice.id),
                ('payment_id.payment_type', '=', 'inbound'),
                ('payment_id.partner_type', '=', 'supplier'),
                ('payment_id.state', 'in', ['received', 'paid', 'partial_used']),
            ]).mapped('amount_to_pay')
        )

        return max(total - already_received, 0.0)

    def _prepare_vendor_bill_line_commands(self):
        self.ensure_one()

        commands = [(5, 0, 0)]
        domain = self._get_moves_domain()

        if not domain:
            return commands

        moves = self.env['account.move'].search(
            domain,
            order='invoice_date_due asc, invoice_date asc, id asc'
        )

        for move in moves:
            available = self._get_available_amount_for_move(move)

            if available <= 0:
                continue

            commands.append((0, 0, {
                'invoice_id': move.id,
                'selected': False,
                'amount_before': abs(move.amount_residual or 0.0),
                'amount_to_pay': 0.0,
                'is_processed': False,
                'source_payment_id': self.source_supplier_payment_id.id if self.source_supplier_payment_id else False,
            }))

        return commands

    def _get_candidate_vendor_bills_for_payment(self):
        self.ensure_one()

        invoices = self.env['account.move']

        if 'reconciled_bill_ids' in self._fields:
            invoices |= self.reconciled_bill_ids

        if 'reconciled_invoice_ids' in self._fields:
            invoices |= self.reconciled_invoice_ids.filtered(lambda m: m.move_type == 'in_invoice')

        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        active_id = self.env.context.get('active_id')

        if active_model == 'account.move':
            ids = active_ids or ([active_id] if active_id else [])
            if ids:
                invoices |= self.env['account.move'].browse(ids).filtered(
                    lambda m: (
                        m.move_type == 'in_invoice'
                        and m.state == 'posted'
                        and m.partner_id == self.partner_id
                        and m.company_id == self.company_id
                    )
                )

        if not invoices:
            refs = []
            for fname in ['memo', 'ref', 'payment_reference', 'communication']:
                if fname in self._fields and self[fname]:
                    refs.append(self[fname])

            refs = list(set([r for r in refs if r]))

            if refs:
                invoices |= self.env['account.move'].search([
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'posted'),
                    ('partner_id', '=', self.partner_id.id),
                    ('company_id', '=', self.company_id.id),
                    '|',
                    ('name', 'in', refs),
                    ('ref', 'in', refs),
                ])

        if not invoices and self.partner_id and self.company_id:
            amount = abs(self.amount or 0.0)
            company_currency = self.company_id.currency_id

            candidates = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('partner_id', '=', self.partner_id.id),
                ('company_id', '=', self.company_id.id),
                ('payment_state', 'in', ['not_paid', 'partial', 'in_payment']),
            ], order='invoice_date_due asc, invoice_date asc, id asc')

            for inv in candidates:
                if company_currency.is_zero(abs(inv.amount_residual or 0.0) - amount):
                    invoices |= inv
                    break

        return invoices.filtered(lambda m: m.move_type == 'in_invoice' and m.state == 'posted')

    def _force_reconcile_vendor_bills(self):
        for payment in self:
            if (
                payment.partner_type != 'supplier'
                or payment.payment_type != 'outbound'
                or not payment.move_id
            ):
                continue

            invoices = payment._get_candidate_vendor_bills_for_payment()
            if not invoices:
                continue

            for invoice in invoices:
                invoice_lines = invoice.line_ids.filtered(
                    lambda l: (
                        l.account_id.account_type in ('liability_payable', 'asset_receivable')
                        and not l.reconciled
                    )
                )

                for inv_line in invoice_lines:
                    payment_lines = payment.move_id.line_ids.filtered(
                        lambda l: (
                            l.account_id == inv_line.account_id
                            and l.partner_id == inv_line.partner_id
                            and not l.reconciled
                        )
                    )

                    if not payment_lines:
                        continue

                    try:
                        (payment_lines[:1] | inv_line).reconcile()
                    except Exception:
                        continue

            payment._ensure_vendor_bill_lines_from_reconciliation()

    def _sync_invoices_after_standard_payment(self, payment):
        invoices = payment._get_candidate_vendor_bills_for_payment()

        if payment.move_id:
            payment_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type in ('liability_payable', 'asset_receivable')
            )

            partials = self.env['account.partial.reconcile']
            for line in payment_lines:
                partials |= line.matched_debit_ids
                partials |= line.matched_credit_ids

            for partial in partials:
                moves = partial.debit_move_id.move_id | partial.credit_move_id.move_id
                invoices |= moves.filtered(lambda m: m.move_type == 'in_invoice')

        self._refresh_invoice_payment_info(invoices)
        return invoices

    def _ensure_vendor_bill_lines_from_reconciliation(self):
        for payment in self:
            if (
                payment.partner_type != 'supplier'
                or payment.payment_type != 'outbound'
                or not payment.move_id
            ):
                continue

            payment_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type in ('liability_payable', 'asset_receivable')
            )

            partials = self.env['account.partial.reconcile']
            for line in payment_lines:
                partials |= line.matched_debit_ids
                partials |= line.matched_credit_ids

            invoice_amounts = {}

            for partial in partials:
                other_line = False

                if partial.debit_move_id in payment_lines:
                    other_line = partial.credit_move_id
                elif partial.credit_move_id in payment_lines:
                    other_line = partial.debit_move_id

                if not other_line:
                    continue

                invoice = other_line.move_id
                if invoice.move_type != 'in_invoice':
                    continue

                invoice_amounts[invoice] = invoice_amounts.get(invoice, 0.0) + abs(partial.amount or 0.0)

            for invoice, paid_amount in invoice_amounts.items():
                if paid_amount <= 0:
                    continue

                current_residual = abs(invoice.amount_residual or 0.0)
                amount_before = current_residual + abs(paid_amount or 0.0)

                existing_line = payment.vendor_bill_line_ids.filtered(
                    lambda l: l.invoice_id.id == invoice.id
                )[:1]

                vals = {
                    'selected': True,
                    'amount_before': amount_before,
                    'amount_to_pay': paid_amount,
                    'amount_processed': paid_amount,
                    'is_processed': True,
                    'processed_payment_id': payment.id,
                    'source_payment_id': False,
                }

                if existing_line:
                    if not existing_line.cancellation_payment_id:
                        existing_line.with_context(skip_amount_to_pay_check=True).write(vals)
                else:
                    vals.update({
                        'payment_id': payment.id,
                        'invoice_id': invoice.id,
                    })
                    self.env['account.payment.vendor.bill.line'].with_context(
                        skip_amount_to_pay_check=True
                    ).create(vals)

    def action_refresh_vendor_bills(self):
        """
        Actualise sans doublon :
        - une seule ligne par facture ;
        - si la facture existe déjà, on met à jour le reste actuel ;
        - aucun contrôle bloquant sur les montants déjà saisis.
        """
        for payment in self:
            if payment.state not in ('draft', 'partial_used', 'received', 'paid'):
                continue

            if payment.partner_type == 'supplier' and payment.payment_type == 'inbound':
                if payment.vendor_bill_line_ids:
                    payment.vendor_bill_line_ids.with_context(skip_amount_to_pay_check=True).unlink()
                continue

            domain = payment._get_moves_domain()
            if not domain:
                continue

            moves = self.env['account.move'].search(
                domain,
                order='invoice_date_due asc, invoice_date asc, id asc'
            )

            valid_move_ids = set(moves.ids)

            for line in payment.vendor_bill_line_ids:
                if line.invoice_id.id not in valid_move_ids and not line.is_processed:
                    line.with_context(skip_amount_to_pay_check=True).unlink()

            existing_by_invoice = {
                line.invoice_id.id: line
                for line in payment.vendor_bill_line_ids
                if line.invoice_id
            }

            commands = []

            for move in moves:
                available = abs(move.amount_residual or 0.0)
                existing_line = existing_by_invoice.get(move.id)

                if existing_line:
                    existing_line.with_context(skip_amount_to_pay_check=True).write({
                        'amount_before': available + abs(existing_line.amount_processed or 0.0),
                    })
                    continue

                if available <= 0:
                    continue

                commands.append((0, 0, {
                    'invoice_id': move.id,
                    'selected': False,
                    'amount_before': available,
                    'amount_to_pay': 0.0,
                    'amount_processed': 0.0,
                    'is_processed': False,
                    'source_payment_id': False,
                }))

            if commands:
                payment.with_context(skip_amount_to_pay_check=True).write({
                    'vendor_bill_line_ids': commands
                })

        return True

    def _break_all_supplier_invoice_payment_links(self, invoices, source_payment=False):
        self.ensure_one()

        invoices = invoices.exists()
        payments = self
        if source_payment:
            payments |= source_payment

        invoice_lines = invoices.mapped('line_ids').filtered(
            lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
        )

        payment_lines = payments.mapped('move_id.line_ids').filtered(
            lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
        )

        all_lines = invoice_lines | payment_lines

        partials = self.env['account.partial.reconcile'].sudo().search([
            '|',
            ('debit_move_id', 'in', all_lines.ids),
            ('credit_move_id', 'in', all_lines.ids),
        ])

        if partials:
            partials.unlink()

        custom_lines = self.env['account.payment.vendor.bill.line'].sudo().search([
            '|',
            ('invoice_id', 'in', invoices.ids),
            '|',
            ('payment_id', 'in', payments.ids),
            ('processed_payment_id', 'in', payments.ids),
        ])

        if custom_lines:
            custom_lines.with_context(skip_amount_to_pay_check=True).unlink()

        # Réconcilier paiement original avec paiement d'annulation,
        # mais PAS avec la facture.
        if source_payment and source_payment.move_id and self.move_id:
            source_lines = source_payment.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
                and not l.reconciled
            )

            cancel_lines = self.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
                and not l.reconciled
            )

            for s_line in source_lines:
                c_line = cancel_lines.filtered(
                    lambda l: l.account_id == s_line.account_id
                    and l.partner_id == s_line.partner_id
                    and not l.reconciled
                )[:1]

                if c_line:
                    try:
                        (s_line | c_line).reconcile()
                    except Exception:
                        pass

        for invoice in invoices:
            invoice.invalidate_recordset()
            invoice.line_ids.invalidate_recordset()

            if hasattr(invoice, '_compute_amount'):
                invoice._compute_amount()

            if hasattr(invoice, '_compute_payment_state'):
                invoice._compute_payment_state()

            for fname in [
                'invoice_payments_widget',
                'invoice_outstanding_credits_debits_widget',
                'payments_widget',
            ]:
                if fname in invoice._fields:
                    try:
                        invoice[fname] = False
                    except Exception:
                        pass

        if source_payment:
            source_payment.with_context(skip_amount_to_pay_check=True).write({
                'state': 'paid'
            })

        self.with_context(skip_amount_to_pay_check=True).write({
            'state': 'received'
        })

        self.env.flush_all()
        self.env.invalidate_all()

        return True
    @api.onchange('partner_id', 'company_id', 'partner_type', 'payment_type', 'amount')
    def _onchange_partner_id_load_vendor_bills(self):
        for payment in self:
            if payment.payment_type != 'inbound':
                payment.source_supplier_payment_id = False

            if payment.state == 'draft':
                payment.vendor_bill_line_ids = payment._prepare_vendor_bill_line_commands()

                if payment.payment_type == 'inbound' and payment.amount > 0:
                    remaining = abs(payment.amount)

                    for line in payment.vendor_bill_line_ids:
                        if remaining <= 0:
                            line.selected = False
                            line.amount_to_pay = 0.0
                            continue

                        max_amount = line._get_max_amount_allowed()
                        amount = min(max_amount, remaining)

                        if amount > 0:
                            line.selected = True
                            line.amount_to_pay = amount
                            remaining -= amount

    @api.onchange('source_supplier_payment_id')
    def _onchange_source_supplier_payment_id(self):
        for payment in self:
            if payment.payment_type != 'inbound':
                continue

            if payment.source_supplier_payment_id:
                payment.amount = abs(payment.source_supplier_payment_id.amount or 0.0)
            else:
                payment.amount = 0.0

            payment.vendor_bill_line_ids = payment._prepare_vendor_bill_line_commands()

            if payment.amount > 0:
                remaining = abs(payment.amount)

                for line in payment.vendor_bill_line_ids:
                    if remaining <= 0:
                        line.selected = False
                        line.amount_to_pay = 0.0
                        continue

                    max_amount = line._get_max_amount_allowed()
                    amount = min(max_amount, remaining)

                    if amount > 0:
                        line.selected = True
                        line.amount_to_pay = amount
                        remaining -= amount

    @api.onchange(
        'vendor_bill_line_ids',
        'vendor_bill_line_ids.selected',
        'vendor_bill_line_ids.amount_to_pay',
        'amount'
    )
    def _onchange_vendor_bill_total_limit(self):
        return

    @api.constrains('vendor_bill_line_ids', 'amount', 'partner_type', 'state')
    def _check_selected_vendor_bill_total(self):
        return

    def _reconcile_supplier_payment_lines(self, selected_lines):
        self.ensure_one()

        invoices_to_sync = self.env['account.move']

        if not self.move_id:
            return invoices_to_sync

        for bill_line in selected_lines:
            invoice = bill_line.invoice_id
            requested_amount = abs(bill_line.amount_to_pay or 0.0)
            already_processed = abs(bill_line.amount_processed or 0.0)
            amount_to_pay = max(requested_amount - already_processed, 0.0)

            if not invoice or amount_to_pay <= 0:
                continue

            payment_lines = self.move_id.line_ids.filtered(
                lambda line: (
                    line.account_id.account_type in ('liability_payable', 'asset_receivable')
                    and not line.reconciled
                    and abs(line.amount_residual or 0.0) > 0
                )
            )

            invoice_lines = invoice.line_ids.filtered(
                lambda line: (
                    line.account_id.account_type in ('liability_payable', 'asset_receivable')
                    and not line.reconciled
                    and abs(line.amount_residual or 0.0) > 0
                )
            )

            if not payment_lines or not invoice_lines:
                continue

            payment_line = payment_lines[:1]
            invoice_line = invoice_lines[:1]

            amount_before = abs(invoice.amount_residual or 0.0)
            max_possible = min(
                abs(payment_line.amount_residual or 0.0),
                abs(invoice_line.amount_residual or 0.0),
            )
            amount = min(amount_to_pay, max_possible)

            if amount <= 0:
                continue

            # IMPORTANT : ne pas utiliser (payment_line | invoice_line).reconcile() ici.
            # reconcile() rapproche automatiquement le maximum possible et force donc
            # tout le paiement sur une seule facture. On crée un partial reconcile
            # limité au montant saisi manuellement sur la ligne.
            if payment_line.balance > 0 and invoice_line.balance < 0:
                debit_line = payment_line
                credit_line = invoice_line
            elif invoice_line.balance > 0 and payment_line.balance < 0:
                debit_line = invoice_line
                credit_line = payment_line
            else:
                # Sécurité si le sens débit/crédit est inattendu.
                lines = payment_line | invoice_line
                debit_line = lines.filtered(lambda l: l.balance > 0)[:1]
                credit_line = lines.filtered(lambda l: l.balance < 0)[:1]

            if not debit_line or not credit_line:
                continue

            self.env['account.partial.reconcile'].with_context(
                skip_vendor_bill_line_auto_create=True
            ).create({
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
                'amount': amount,
                'debit_amount_currency': amount if debit_line.currency_id else 0.0,
                'credit_amount_currency': amount if credit_line.currency_id else 0.0,
            })

            new_processed_amount = already_processed + amount

            bill_line.with_context(skip_amount_to_pay_check=True).write({
                'amount_before': amount_before,
                'amount_to_pay': new_processed_amount,
                'amount_processed': new_processed_amount,
                'is_processed': True,
                'processed_payment_id': self.id,
                'source_payment_id': False,
            })

            invoices_to_sync |= invoice

        return invoices_to_sync

    def _unreconcile_supplier_invoice_amount(self, invoice, amount_to_cancel, source_payment=False):
        self.ensure_one()

        if not invoice:
            return 0.0

        move_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
        )

        if source_payment and source_payment.move_id:
            move_lines |= source_payment.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
            )

        if self.move_id:
            move_lines |= self.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
            )

        partials = self.env['account.partial.reconcile'].sudo().search([
            '|',
            ('debit_move_id', 'in', move_lines.ids),
            ('credit_move_id', 'in', move_lines.ids),
        ])

        if partials:
            partials.unlink()

        invoice.invalidate_recordset()
        invoice.line_ids.invalidate_recordset()

        for fname in [
            'invoice_payments_widget',
            'invoice_outstanding_credits_debits_widget',
            'payments_widget',
        ]:
            if fname in invoice._fields:
                try:
                    invoice[fname] = False
                except Exception:
                    pass

        self.env.flush_all()
        self.env.invalidate_all()

        return abs(amount_to_cancel or 0.0)
    def _reconcile_source_payment_with_cancellation(self, source_payment):
        self.ensure_one()

        if not source_payment or not source_payment.move_id or not self.move_id:
            return False

        source_lines = source_payment.move_id.line_ids.filtered(
            lambda l: (
                l.account_id.account_type in ('liability_payable', 'asset_receivable')
                and not l.reconciled
            )
        )

        cancellation_lines = self.move_id.line_ids.filtered(
            lambda l: (
                l.account_id.account_type in ('liability_payable', 'asset_receivable')
                and not l.reconciled
            )
        )

        for source_line in source_lines:
            matching_lines = cancellation_lines.filtered(
                lambda l: (
                    l.account_id == source_line.account_id
                    and l.partner_id == source_line.partner_id
                    and not l.reconciled
                )
            )

            if matching_lines:
                try:
                    (source_line | matching_lines[:1]).reconcile()
                except Exception:
                    continue

        source_payment.invalidate_recordset()
        source_payment.move_id.line_ids.invalidate_recordset()
        self.invalidate_recordset()
        self.move_id.line_ids.invalidate_recordset()

        return True

    def _mark_source_payment_after_receive(self, source_payment):
        if not source_payment:
            return True

        source_payment.with_context(skip_amount_to_pay_check=True).write({
            'state': 'paid'
        })

        return True

    def _hard_clear_vendor_bill_links(self, invoices, source_payment=False):
        self.ensure_one()

        if not invoices:
            return True

        domain = [('invoice_id', 'in', invoices.ids)]

        if source_payment:
            domain = ['|',
                ('payment_id', '=', source_payment.id),
                ('invoice_id', 'in', invoices.ids),
            ]

        lines = self.env['account.payment.vendor.bill.line'].sudo().search(domain)

        if lines:
            lines.with_context(skip_amount_to_pay_check=True).unlink()

        return True
    def _unreconcile_supplier_payment_lines(self, selected_lines):
        self.ensure_one()

        invoices = selected_lines.exists().mapped('invoice_id').filtered(
            lambda m: m.move_type == 'in_invoice'
        )

        if not invoices:
            return self.env['account.move']

        self._break_all_supplier_invoice_payment_links(
            invoices,
            source_payment=self.source_supplier_payment_id
        )

        return invoices
    def _hard_break_invoice_payment_links(self, invoices):
        """Annule l'affectation fournisseur sans supprimer les paiements.

        Résultat voulu :
        - la facture fournisseur redevient non payée ;
        - l'ancien paiement fournisseur reste dans Odoo mais ne ressort plus
          dans le smart-button Paiements de la facture ;
        - le paiement d'annulation passe en Reçu et ne ressort pas non plus
          dans ce smart-button ;
        - si la facture est repayée plus tard, seul le nouveau paiement ressort.
        """
        self.ensure_one()

        invoices = invoices.exists().filtered(lambda m: m.move_type == 'in_invoice')

        hide_vals = {}
        if 'hide_from_vendor_bill_button' in self._fields:
            hide_vals['hide_from_vendor_bill_button'] = True

        if not invoices:
            vals = {'state': 'received'}
            vals.update(hide_vals)
            self.with_context(skip_amount_to_pay_check=True).write(vals)
            return True

        payments = self
        source_payment = self.source_supplier_payment_id
        if source_payment:
            payments |= source_payment

        AccountLine = self.env['account.move.line'].sudo()
        Partial = self.env['account.partial.reconcile'].sudo()
        Full = self.env['account.full.reconcile'].sudo()

        invoice_lines = invoices.mapped('line_ids').filtered(
            lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
        )
        payment_lines = payments.mapped('move_id.line_ids').filtered(
            lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')
        )
        all_lines = (invoice_lines | payment_lines).exists()

        # 1) Casser les rapprochements côté facture avec l'API Odoo.
        if invoice_lines:
            try:
                invoice_lines.remove_move_reconcile()
            except Exception:
                pass

        # 2) Sécurité : supprimer tout partial reconcile qui touche facture/paiements.
        if all_lines:
            partials = Partial.search([
                '|',
                ('debit_move_id', 'in', all_lines.ids),
                ('credit_move_id', 'in', all_lines.ids),
            ])
            full_ids = partials.mapped('full_reconcile_id').ids

            if partials:
                partials.unlink()

            self.env.cr.execute("""
                UPDATE account_move_line
                   SET full_reconcile_id = NULL,
                       matching_number = NULL
                 WHERE id = ANY(%s)
            """, [all_lines.ids])

            if full_ids:
                orphan_full = Full.browse(full_ids).exists().filtered(
                    lambda f: not AccountLine.search_count([('full_reconcile_id', '=', f.id)])
                )
                if orphan_full:
                    orphan_full.unlink()

        # 3) Supprimer les lignes custom qui recréent les liens visuels.
        custom_lines = self.env['account.payment.vendor.bill.line'].sudo().search([
            '|', '|', '|', '|',
            ('invoice_id', 'in', invoices.ids),
            ('payment_id', 'in', payments.ids),
            ('processed_payment_id', 'in', payments.ids),
            ('source_payment_id', 'in', payments.ids),
            ('cancellation_payment_id', 'in', payments.ids),
        ])
        if custom_lines:
            custom_lines.with_context(skip_amount_to_pay_check=True).unlink()

        payments.with_context(skip_amount_to_pay_check=True).write({
            'vendor_bill_line_ids': [(5, 0, 0)]
        })

        # 4) Recalcul facture + widgets.
        for invoice in invoices:
            invoice.invalidate_recordset()
            invoice.line_ids.invalidate_recordset()

            if hasattr(invoice, '_compute_amount'):
                invoice._compute_amount()
            if hasattr(invoice, '_compute_payment_state'):
                invoice._compute_payment_state()

            # Forcer la facture non payée après annulation d'affectation.
            if invoice.payment_state != 'not_paid':
                self.env.cr.execute("""
                    UPDATE account_move
                       SET payment_state = 'not_paid'
                     WHERE id = %s
                       AND move_type = 'in_invoice'
                """, [invoice.id])
                invoice.invalidate_recordset(['payment_state'])

            for fname in [
                'invoice_payments_widget',
                'invoice_outstanding_credits_debits_widget',
                'payments_widget',
            ]:
                if fname in invoice._fields:
                    try:
                        invoice[fname] = False
                    except Exception:
                        pass

        # 5) Masquer uniquement les paiements annulés/reçus du smart-button.
        vals_current = {'state': 'received'}
        vals_current.update(hide_vals)
        self.with_context(skip_amount_to_pay_check=True).write(vals_current)

        if source_payment:
            vals_source = {'state': 'paid'}
            if 'hide_from_vendor_bill_button' in source_payment._fields:
                vals_source['hide_from_vendor_bill_button'] = True
            source_payment.with_context(skip_amount_to_pay_check=True).write(vals_source)

        self.env.flush_all()
        self.env.invalidate_all()
        return True

    def action_post(self):
        """Valide le paiement fournisseur en gardant les 2 modes :

        1) Paiement standard Odoo depuis la facture :
           - aucune ligne personnalisée sélectionnée ;
           - on laisse Odoo poster le paiement ;
           - puis on synchronise les factures liées par la réconciliation standard.

        2) Paiement personnalisé depuis la liste vendor_bill_line_ids :
           - lignes sélectionnées avec montant ;
           - on fait le rapprochement partiel selon les montants saisis.
        """
        payments_to_post = self.filtered(lambda p: p.state == 'draft')
        res = True

        if payments_to_post:
            res = super(AccountPayment, payments_to_post).action_post()

        for payment in self:
            if payment.partner_type != 'supplier':
                continue

            selected_lines = payment.vendor_bill_line_ids.filtered(
                lambda l: l.selected and l.amount_to_pay > 0
            )

            if payment.payment_type == 'outbound':
                invoices_to_sync = self.env['account.move']

                if selected_lines:
                    # =====================================================
                    # MODE PERSONNALISÉ : paiement depuis ta liste de factures
                    # =====================================================
                    invoices_to_sync = payment._reconcile_supplier_payment_lines(selected_lines)

                    selected_lines.with_context(skip_amount_to_pay_check=True).write({
                        'is_processed': True,
                        'processed_payment_id': payment.id,
                        'source_payment_id': False,
                    })

                else:
                    # =====================================================
                    # MODE STANDARD : paiement lancé depuis la facture Odoo
                    # =====================================================
                    # Odoo a déjà créé/posté le paiement avec le contexte de la facture.
                    # On force seulement la détection et la synchro pour ton smart-button/liste.
                    payment._force_reconcile_vendor_bills()
                    invoices_to_sync = payment._sync_invoices_after_standard_payment(payment)
                    payment._ensure_vendor_bill_lines_from_reconciliation()

                if 'hide_from_vendor_bill_button' in payment._fields:
                    payment.with_context(skip_amount_to_pay_check=True).write({
                        'hide_from_vendor_bill_button': False,
                    })

                if invoices_to_sync:
                    self._refresh_invoice_payment_info(invoices_to_sync)

                remaining_after = payment._get_payment_available_amount()

                if remaining_after > 0:
                    payment.with_context(skip_amount_to_pay_check=True).write({'state': 'partial_used'})
                else:
                    payment.with_context(skip_amount_to_pay_check=True).write({'state': 'paid'})

                # Ne pas supprimer les lignes déjà traitées ; seulement charger les factures encore disponibles.
                payment.action_refresh_vendor_bills()

            elif payment.payment_type == 'inbound':
                # =====================================================
                # MODE RÉCEPTION/ANNULATION FOURNISSEUR : ton comportement actuel
                # =====================================================
                invoices = selected_lines.mapped('invoice_id').exists()
                if not invoices:
                    invoices = payment.vendor_bill_line_ids.mapped('invoice_id').exists()

                if not invoices and payment.source_supplier_payment_id:
                    payment.source_supplier_payment_id._ensure_vendor_bill_lines_from_reconciliation()
                    invoices = payment.source_supplier_payment_id.vendor_bill_line_ids.mapped('invoice_id').exists()

                if invoices:
                    payment._hard_break_invoice_payment_links(invoices)
                else:
                    payment.vendor_bill_line_ids.with_context(skip_amount_to_pay_check=True).unlink()
                    vals = {'state': 'received'}
                    if 'hide_from_vendor_bill_button' in payment._fields:
                        vals['hide_from_vendor_bill_button'] = True
                    payment.with_context(skip_amount_to_pay_check=True).write(vals)

                self.env.flush_all()
                self.env.invalidate_all()

        return res

    def action_confirm_remaining(self):
        for payment in self:
            if payment.state not in ('partial_used', 'received', 'paid'):
                raise ValidationError(_("Ce bouton est réservé aux paiements partiellement utilisés."))

            selected_lines = payment.vendor_bill_line_ids.filtered(
                lambda l: l.selected and l.amount_to_pay > 0
            )

            if not selected_lines:
                raise ValidationError(_("Veuillez sélectionner au moins une facture à traiter."))

        return self.action_post()

    def get_payment_order_lines(self):
        self.ensure_one()
        return self.vendor_bill_line_ids.filtered(
            lambda l: l.processed_payment_id == self and l.selected
        )

    def action_print_payment_order(self):
        self.ensure_one()
        return self.env.ref('cargo_fleet.action_report_payment_order').report_action(self)

    def unlink(self):
        for payment in self:
            if payment.vendor_bill_line_ids:
                payment.vendor_bill_line_ids.with_context(
                    skip_amount_to_pay_check=True
                ).unlink()
        return super().unlink()


class AccountPaymentVendorBillLine(models.Model):
    _name = 'account.payment.vendor.bill.line'
    _description = 'Ligne pièces fournisseur du paiement'
    _order = 'is_fully_paid asc, invoice_date_due asc, invoice_date asc, id asc'

    payment_id = fields.Many2one(
        'account.payment',
        string="Paiement",
        required=True,
        ondelete='cascade'
    )

    source_payment_id = fields.Many2one(
        'account.payment',
        string="Paiement annulé",
        readonly=True,
        copy=False
    )

    processed_payment_id = fields.Many2one(
        'account.payment',
        string="Paiement associé",
        readonly=True,
        copy=False
    )

    cancellation_payment_id = fields.Many2one(
        'account.payment',
        string="Paiement d'annulation",
        readonly=True,
        copy=False
    )

    is_processed = fields.Boolean(
        string="Déjà traité",
        default=False,
        readonly=True,
        copy=False
    )

    is_fully_paid = fields.Boolean(
        string="Totalement payée",
        compute="_compute_is_fully_paid",
        store=True,
    )

    company_id = fields.Many2one(related='payment_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='payment_id.currency_id', store=True, readonly=True)

    selected = fields.Boolean(string="Sélectionner")

    invoice_id = fields.Many2one(
        'account.move',
        string="Pièce fournisseur",
        required=True,
        domain=[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]
    )

    invoice_name = fields.Char(related='invoice_id.name', string="Numéro pièce", readonly=True)
    invoice_ref = fields.Char(related='invoice_id.ref', string="Référence", readonly=True)
    invoice_date = fields.Date(related='invoice_id.invoice_date', string="Date pièce", readonly=True)
    invoice_date_due = fields.Date(related='invoice_id.invoice_date_due', string="Date échéance", readonly=True)
    move_type = fields.Selection(related='invoice_id.move_type', string="Type pièce", readonly=True)

    amount_untaxed = fields.Monetary(related='invoice_id.amount_untaxed', string="Montant HT", readonly=True)
    amount_tax = fields.Monetary(related='invoice_id.amount_tax', string="Taxe", readonly=True)
    amount_total = fields.Monetary(related='invoice_id.amount_total', string="Montant TTC", readonly=True)
    amount_residual = fields.Monetary(related='invoice_id.amount_residual', string="Reste actuel", readonly=True)

    amount_before = fields.Monetary(
        string="Montant avant",
        currency_field='currency_id',
        readonly=True,
        copy=False,
        default=0.0
    )

    amount_remaining_after = fields.Monetary(
        string="Montant après",
        currency_field='currency_id',
        compute='_compute_amount_remaining_after',
        readonly=True
    )

    payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string="Statut",
        readonly=True
    )

    amount_to_pay = fields.Monetary(
        string="Montant à traiter",
        required=True,
        default=0.0
    )

    amount_processed = fields.Monetary(
        string="Montant déjà traité",
        currency_field='currency_id',
        default=0.0,
        copy=False,
        readonly=True,
    )

    @api.depends('invoice_id.payment_state', 'invoice_id.amount_residual')
    def _compute_is_fully_paid(self):
        for line in self:
            line.is_fully_paid = bool(
                line.invoice_id
                and line.invoice_id.payment_state in ('paid', 'in_payment')
                and abs(line.invoice_id.amount_residual or 0.0) <= 0.00001
            )

    @api.depends('amount_before', 'amount_to_pay', 'payment_id.payment_type')
    def _compute_amount_remaining_after(self):
        for line in self:
            before = abs(line.amount_before or 0.0)
            treated = abs(line.amount_to_pay or 0.0)

            if not before and line.invoice_id and not line.is_processed:
                before = abs(line.invoice_id.amount_residual or 0.0)

            if line.payment_id.payment_type == 'outbound':
                line.amount_remaining_after = max(before - treated, 0.0)
            elif line.payment_id.payment_type == 'inbound':
                line.amount_remaining_after = before + treated
            else:
                line.amount_remaining_after = before

    def _get_max_amount_allowed(self):
        self.ensure_one()

        if not self.invoice_id or not self.payment_id:
            return 0.0

        if self.payment_id.payment_type == 'inbound':
            return self.payment_id._get_paid_amount_by_source_payment(self.invoice_id)

        if self.payment_id.payment_type != 'outbound':
            return 0.0

        return abs(self.amount_to_pay or 0.0) + abs(self.invoice_id.amount_residual or 0.0) + abs(self.payment_id.amount or 0.0)

    @api.onchange('selected')
    def _onchange_selected(self):
        for line in self:
            if line.selected:
                line.amount_before = abs(line.invoice_id.amount_residual or 0.0) if line.invoice_id else 0.0
                if not line.amount_to_pay:
                    line.amount_to_pay = 0.0
            else:
                line.amount_to_pay = 0.0

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        for line in self:
            if line.invoice_id and not line.is_processed:
                line.amount_before = abs(line.invoice_id.amount_residual or 0.0)
                line.amount_to_pay = 0.0
                line.selected = False

    @api.onchange('amount_to_pay')
    def _onchange_amount_to_pay(self):
        for line in self:
            if line.invoice_id and not line.amount_before:
                line.amount_before = abs(line.invoice_id.amount_residual or 0.0)

            if line.amount_to_pay < 0:
                raise ValidationError(_("Le montant ne peut pas être négatif."))

            # IMPORTANT : on autorise la modification d'une ligne déjà traitée.
            # On ne bloque plus avec max_amount, sinon une ligne payée devient impossible à corriger.
            if line.amount_to_pay > 0:
                line.selected = True
    @api.constrains('amount_to_pay', 'selected')
    def _check_amount_to_pay(self):
        if self.env.context.get('skip_amount_to_pay_check'):
            return

        for line in self:
            if line.amount_to_pay < 0:
                raise ValidationError(_("Le montant ne peut pas être négatif."))

    def action_remove_line(self):
        for line in self:
            if line.payment_id.state not in ('draft', 'partial_used', 'received', 'paid'):
                raise ValidationError(_("Vous ne pouvez supprimer une ligne que si le paiement est en brouillon ou partiellement utilisé."))

            line.with_context(skip_amount_to_pay_check=True).unlink()


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_processed') and vals.get('amount_to_pay') and not vals.get('amount_processed'):
                vals['amount_processed'] = vals.get('amount_to_pay')
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals or {})

        # Quand on modifie une ancienne ligne traitée qui n'avait pas encore
        # amount_processed, on fixe l'ancien montant comme déjà traité.
        # Ainsi, au prochain Confirmer, Odoo ne traite que la différence.
        if 'amount_to_pay' in vals and not self.env.context.get('skip_amount_to_pay_check'):
            for line in self:
                if line.is_processed and not line.amount_processed:
                    line.with_context(skip_amount_to_pay_check=True).write({
                        'amount_processed': abs(line.amount_to_pay or 0.0),
                    })

        return super().write(vals)


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        partials = super().create(vals_list)

        if self.env.context.get('skip_vendor_bill_line_auto_create'):
            return partials

        payments = self.env['account.payment']

        for partial in partials:
            moves = partial.debit_move_id.move_id | partial.credit_move_id.move_id

            payments |= self.env['account.payment'].search([
                ('move_id', 'in', moves.ids),
                ('partner_type', '=', 'supplier'),
                ('payment_type', '=', 'outbound'),
            ])

        if payments:
            payments._ensure_vendor_bill_lines_from_reconciliation()

        return partials