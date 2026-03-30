from odoo import models, fields, api
from datetime import date


class TakGrossProfitWizard(models.TransientModel):
    _name = 'tak.gross.profit.wizard'
    _description = 'Gross Profit Report Wizard'

    def _default_date_from(self):
        today = date.today()
        return date(today.year, 1, 1)

    def _default_date_to(self):
        today = date.today()
        return date(today.year, 12, 31)

    date_from = fields.Date(default=_default_date_from, required=True)
    date_to = fields.Date(default=_default_date_to, required=True)

    product_id = fields.Many2one('product.product')
    partner_id = fields.Many2one('res.partner')
    category_id = fields.Many2one('product.category')

    analytic_account_id = fields.Many2one('account.analytic.account')

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    group_by = fields.Selection([
        ('product', 'Product'),
        ('partner', 'Customer'),
        ('category', 'Product Category'),
    ], default='product', required=True)
    
    file_data = fields.Binary("File", readonly=True)
    file_name = fields.Char("File Name", readonly=True)

    def action_print_pdf(self):
        return self.env.ref(
            'tak_gross_profit_report.action_report_gross_profit'
        ).report_action(self)

    def action_print_excel(self):
        return self._generate_excel()
    
    def _generate_excel(self):
        import xlsxwriter
        import base64
        from io import BytesIO

        report = self.env['report.tak_gross_profit_report.report_gross_profit']
        data = report._get_lines(self)

        lines = data['lines']
        totals = data.get('totals', {})

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Gross Profit")

        bold = workbook.add_format({'bold': True})
        money = workbook.add_format({'num_format': '#,##0.00'})
        percent_fmt = workbook.add_format({'num_format': '0.00'})
        total_fmt = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
        total_percent_fmt = workbook.add_format({'bold': True, 'num_format': '0.00'})

        row = 0
        sheet.write(row, 0, "Gross Profit Report", bold)
        row += 2

        col = 0

        if self.group_by == 'product':
            sheet.write(row, col, "Category", bold)
            col += 1

        sheet.write(row, col, "Item", bold)
        sheet.write(row, col + 1, "Actual Revenue", bold)
        sheet.write(row, col + 2, "Actual Cost", bold)
        sheet.write(row, col + 3, "Gross Profit", bold)
        sheet.write(row, col + 4, "%", bold)

        row += 1

        for l in lines:
            col = 0

            if self.group_by == 'product':
                sheet.write(row, col, l.get('category_name', ''))
                col += 1

            sheet.write(row, col, l['name'])
            sheet.write(row, col + 1, l['revenue'], money)
            sheet.write(row, col + 2, l['cost'], money)
            sheet.write(row, col + 3, l['gross_profit'], money)
            sheet.write(row, col + 4, l['percentage'], percent_fmt)

            row += 1

        row += 1
        col = 0

        if self.group_by == 'product':
            col += 1

        sheet.write(row, col, "GRAND TOTAL", bold)
        sheet.write(row, col + 1, totals.get('revenue', 0.0), total_fmt)
        sheet.write(row, col + 2, totals.get('cost', 0.0), total_fmt)
        sheet.write(row, col + 3, totals.get('gross_profit', 0.0), total_fmt)
        sheet.write(row, col + 4, totals.get('percentage', 0.0), total_percent_fmt)

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        file_name = "Gross_Profit_Report.xlsx"

        self.write({
            'file_data': file_data,
            'file_name': file_name,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=tak.gross.profit.wizard&id={self.id}&field=file_data&filename_field=file_name&download=true',
            'target': 'self',
        }