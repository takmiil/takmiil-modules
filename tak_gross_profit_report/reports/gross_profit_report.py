from odoo import models, api


class ReportGrossProfit(models.AbstractModel):
    _name = 'report.tak_gross_profit_report.report_gross_profit'
    _description = 'Gross Profit Report'

    def _get_lines(self, wizard):

        domain = [
            ('date', '>=', wizard.date_from),
            ('date', '<=', wizard.date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', wizard.company_id.id),        
            ('account_id.account_type', 'in', [
                'income', 'income_other',
                'expense', 'expense_other',
                'expense_depreciation', 'expense_direct_cost'
            ])
        ]

        if wizard.product_id:
            domain.append(('product_id', '=', wizard.product_id.id))

        if wizard.partner_id:
            domain.append(('partner_id', '=', wizard.partner_id.id))

        if wizard.category_id:
            domain.append(('product_id.categ_id', '=', wizard.category_id.id))

        if wizard.analytic_account_id:
            domain.append((
                'analytic_distribution',
                'ilike',
                f'"{wizard.analytic_account_id.id}":'
            ))

        if wizard.group_by == 'product':
            group_field = 'product_id'
        elif wizard.group_by == 'partner':
            group_field = 'partner_id'
        else:
            group_field = 'product_id.categ_id'

        lines = self.env['account.move.line'].search(domain)

        result = {}
        for line in lines:
            key = getattr(line, group_field.split('.')[0])
            if group_field == 'product_id.categ_id':
                key = line.product_id.categ_id

            if not key:
                continue

            result.setdefault(key.id, {
                'name': key.display_name,
                'revenue': 0.0,
                'cost': 0.0,
            })
            
            # Add category only if grouping by product
            if wizard.group_by == 'product':
                result[key.id]['category_name'] = (
                    key.categ_id.display_name if key.categ_id else ''
                )
            
            account_type = line.account_id.account_type

            if account_type.startswith('income'):
                # Reverse income sign (like P&L report)
                result[key.id]['revenue'] += -line.balance
            elif account_type.startswith('expense'):
                # Expenses remain positive
                result[key.id]['cost'] += line.balance
            # old way
            # if line.account_id.account_type.startswith('income'):
            #     result[key.id]['revenue'] += line.balance
            # else:
            #     result[key.id]['cost'] += abs(line.balance)

        final_lines = []
        for val in result.values():
            revenue = val['revenue']
            cost = val['cost']
            gross = revenue - cost
            percent = (gross / revenue * 100) if revenue else 0.0

            val.update({
                'gross_profit': gross,
                'percentage': percent
            })

            final_lines.append(val)

        total_revenue = sum(l['revenue'] for l in final_lines)
        total_cost = sum(l['cost'] for l in final_lines)
        total_gross = total_revenue - total_cost
        total_percent = (total_gross / total_revenue * 100) if total_revenue else 0.0

        return {
            'lines': final_lines,
            'totals': {
                'revenue': total_revenue,
                'cost': total_cost,
                'gross_profit': total_gross,
                'percentage': total_percent,
            }
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['tak.gross.profit.wizard'].browse(docids)

        data = self._get_lines(wizard)

        return {
            'docs': wizard,
            'lines': data['lines'],
            'totals': data['totals'],
            'date_from': wizard.date_from,
            'date_to': wizard.date_to,
            'currency': wizard.currency_id,
            'group_by': wizard.group_by,
        }