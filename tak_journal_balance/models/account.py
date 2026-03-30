from odoo import _, api, fields, models


class Journal(models.Model):
    _inherit = "account.journal"

    def _get_journal_balance(self, account_id, use_foreign_currency=False):
        field = 'amount_currency' if use_foreign_currency else 'debit - credit'
        query = """
            SELECT sum(%s)
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            WHERE aml.account_id = %%s AND am.state = 'posted'
        """ % field
        
        self.env.cr.execute(query, (account_id,))
        return (self.env.cr.fetchone() or [0.0])[0] or 0.0


    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super(Journal, self)._fill_bank_cash_dashboard_data(dashboard_data)

        for journal in self.filtered(lambda j: j.type in ('bank', 'cash')):
            if journal.id not in dashboard_data:
                continue

            is_foreign = journal.currency_id and journal.currency_id != journal.company_id.currency_id
            balance = self._get_journal_balance(journal.default_account_id.id, use_foreign_currency=is_foreign)
            
            currency = journal.currency_id or journal.company_id.currency_id
            dashboard_data[journal.id]['balance'] = currency.format(balance)