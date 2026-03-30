from odoo import models, fields, api
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)



class JournalStatementWizard(models.TransientModel):
    _name = 'journal.statement.wizard'
    _description = 'Journal Statement Wizard'


    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=True,
        help='Select one or more journals to generate the statement'
    )
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    
   
    

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                'warning': {
                    'title': 'Invalid Date Range',
                    'message': 'Date From must be before Date To.'
                }
            }

    def action_print_report(self):
        """Generate and print the journal statement report."""
        self.ensure_one()
        
        if not self.journal_ids:
            raise UserError("Please select at least one journal.")
        
        if self.date_from > self.date_to:
            raise UserError("Date From must be before Date To.")

        data = {
            'journal_ids': self.journal_ids.ids,
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
        }
        
        return self.env.ref('tak_journal_statement.action_report_journal_statement').report_action(self, data=data)