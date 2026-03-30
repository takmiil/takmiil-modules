from odoo import models, api, fields
from odoo.exceptions import UserError
from collections import defaultdict


class ReportJournalStatement(models.AbstractModel):
    _name = 'report.tak_journal_statement.report_journal_statement'
    _description = 'Journal Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            raise UserError("No data provided for the report.")

        journal_ids = data.get('journal_ids', [])
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        if not journal_ids:
            raise UserError("No journals selected.")

        journals = self.env['account.journal'].browse(journal_ids)
        
        # Build the report data grouped by journal
        report_data = []
        grand_total_debit = 0.0
        grand_total_credit = 0.0
        grand_total_balance = 0.0  # Sum of all journal final balances

        for journal in journals.sorted(key=lambda j: j.name):
            journal_data = self._get_journal_data(journal, date_from, date_to)
            if journal_data['lines'] or journal_data['previous_balance'] != 0:
                report_data.append(journal_data)
                grand_total_debit += journal_data['total_debit']
                grand_total_credit += journal_data['total_credit']
                # FIX: Grand total balance is sum of all journal final balances
                grand_total_balance += journal_data['final_balance']

        return {
            'doc_ids': docids,
            'doc_model': 'journal.statement.wizard',
            'docs': self.env['journal.statement.wizard'].browse(docids),
            'data': data,
            'journals_data': report_data,
            'date_from': date_from,
            'date_to': date_to,
            'grand_total_debit': grand_total_debit,
            'grand_total_credit': grand_total_credit,
            'grand_total_balance': grand_total_balance,  # Now correctly summed from subtotals
            'currency': self.env.company.currency_id,
        }

    def _get_journal_data(self, journal, date_from, date_to):
        """Get all statement data for a specific journal."""
        AccountMoveLine = self.env['account.move.line']
        
        # Get default account for this journal
        default_account = journal.default_account_id
        
        # Calculate previous balance (balance before date_from)
        previous_balance = 0.0
        if default_account:
            prev_domain = [
                ('account_id', '=', default_account.id),
                ('date', '<', date_from),
                ('parent_state', '=', 'posted'),
            ]
            prev_lines = AccountMoveLine.search(prev_domain)
            previous_balance = sum(prev_lines.mapped('balance'))

        # Get transactions within date range, sorted by ID (creation order)
        domain = [
            ('account_id', '=', default_account.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('parent_state', '=', 'posted'),
        ]
        
        move_lines = AccountMoveLine.search(domain, order='id asc')
        
        lines = []
        running_balance = previous_balance
        total_debit = 0.0
        total_credit = 0.0

        for line in move_lines:
            debit = abs(line.balance) if line.balance > 0 else 0.0
            credit = abs(line.balance) if line.balance < 0 else 0.0
            
            running_balance += line.balance
            
            # Determine reference
            reference = line.move_id.name
            if line.move_id.origin_payment_id:
                reference = line.move_id.origin_payment_id.name or reference
            description = f"{line.name}-{line.move_id.payment_reference}" if line.move_id.payment_reference else line.name or line.move_id.ref
            partner = line.partner_id.name or '-'
            lines.append({
                'date': line.date,
                'reference': reference,
                'description': description,
                'partner': partner,
                'debit': debit,
                'credit': credit,
                'balance': running_balance,
                'move_id': line.move_id.id,
            })
            
            total_debit += debit
            total_credit += credit

        return {
            'journal': journal,
            'journal_name': journal.name,
            'journal_code': journal.code,
            'default_account': default_account,
            'account_name': default_account.name if default_account else 'N/A',
            'account_code': default_account.code if default_account else 'N/A',
            'previous_balance': previous_balance,
            'lines': lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
            # Subtotal for this period only
            'total_balance': total_debit - total_credit,
            # Final balance includes previous balance + all transactions
            'final_balance': running_balance,
        }