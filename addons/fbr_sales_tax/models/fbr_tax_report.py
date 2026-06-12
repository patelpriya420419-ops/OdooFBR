import base64
import io

from odoo import models, fields, api
from odoo.exceptions import UserError

try:
    import xlsxwriter
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False


class FbrTaxReport(models.TransientModel):
    _name = 'fbr.tax.report'
    _description = 'FBR Sales Tax Report'

    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date To', required=True,
                          default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    report_lang = fields.Selection([
        ('en_US', 'English'),
        ('ur', 'Urdu (اردو)'),
    ], string='Report Language', default='en_US', help='Select the language for your report')

    # Computed summary fields
    total_sales = fields.Float(string='Total Sales', compute='_compute_totals')
    total_purchases = fields.Float(string='Total Purchases', compute='_compute_totals')
    output_tax = fields.Float(string='Output Tax', compute='_compute_totals')
    input_tax = fields.Float(string='Input Tax', compute='_compute_totals')
    net_tax_payable = fields.Float(string='Net Tax Payable', compute='_compute_totals')

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_totals(self):
        for rec in self:
            sales_data = rec._get_sales_data()
            purchase_data = rec._get_purchase_data()
            rec.total_sales = sum(l['taxable_amount'] for l in sales_data)
            rec.total_purchases = sum(l['taxable_amount'] for l in purchase_data)
            rec.output_tax = sum(l['gst_amount'] for l in sales_data)
            rec.input_tax = sum(l['gst_amount'] for l in purchase_data)
            rec.net_tax_payable = rec.output_tax - rec.input_tax


    def _get_sales_data(self):
        domain = [
            ('move_id.move_type', 'in', ['out_invoice']),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('move_id.company_id', '=', self.company_id.id),
        ]
        lines = self.env['account.move.line'].search(domain)
        result = []
        invoices = lines.mapped('move_id')
        for inv in invoices:
            inv_lines = lines.filtered(lambda l: l.move_id == inv)
            taxable = sum(inv_lines.mapped('price_subtotal'))
            gst = sum(inv_lines.mapped('price_total')) - taxable
            result.append({
                'date': inv.invoice_date,
                'invoice_no': inv.name,
                'customer': inv.partner_id.name,
                'description': ', '.join(inv_lines.mapped('name') or ['-']),
                'taxable_amount': taxable,
                'gst_amount': gst,
                'total': taxable + gst,
            })
        return result

    def _get_purchase_data(self):
        domain = [
            ('move_id.move_type', 'in', ['in_invoice']),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('move_id.company_id', '=', self.company_id.id),
        ]
        lines = self.env['account.move.line'].search(domain)
        result = []
        bills = lines.mapped('move_id')
        for bill in bills:
            bill_lines = lines.filtered(lambda l: l.move_id == bill)
            taxable = sum(bill_lines.mapped('price_subtotal'))
            gst = sum(bill_lines.mapped('price_total')) - taxable
            result.append({
                'date': bill.invoice_date,
                'invoice_no': bill.name,
                'supplier': bill.partner_id.name,
                'taxable_amount': taxable,
                'gst_amount': gst,
                'total': taxable + gst,
            })
        return result

    def action_print_sales_register(self):
        return self.env.ref('fbr_sales_tax.action_report_fbr_sales_register').report_action(self)

    def action_print_purchase_register(self):
        return self.env.ref('fbr_sales_tax.action_report_fbr_purchase_register').report_action(self)

    def action_print_monthly_return(self):
        return self.env.ref('fbr_sales_tax.action_report_fbr_monthly_return').report_action(self)

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, company_id=None):
        date_to = date_to or fields.Date.context_today(self)
        date_from = date_from or date_to.replace(day=1)
        company = company_id and self.env['res.company'].browse(company_id) or self.env.company
        report = self.new({
            'date_from': date_from,
            'date_to': date_to,
            'company_id': company.id,
        })
        return {
            'total_sales': report.total_sales,
            'total_purchases': report.total_purchases,
            'output_tax': report.output_tax,
            'input_tax': report.input_tax,
            'net_tax_payable': report.net_tax_payable,
            'month': date_to.strftime('%B %Y'),
            'company_id': company.id,
            'currency_id': company.currency_id.id,
        }

    def _build_xlsx_attachment(self):
        self.ensure_one()
        if not HAS_XLSX:
            raise UserError('xlsxwriter is required for Excel export. Install it via pip.')

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)

        # Styles
        bold = wb.add_format({'bold': True, 'bg_color': '#1a5276', 'font_color': 'white', 'border': 1})
        header = wb.add_format({'bold': True, 'bg_color': '#2e86c1', 'font_color': 'white', 'border': 1, 'align': 'center'})
        money = wb.add_format({'num_format': '#,##0.00', 'border': 1})
        label = wb.add_format({'bold': True, 'border': 1})
        total_fmt = wb.add_format({'bold': True, 'num_format': '#,##0.00', 'bg_color': '#d5e8d4', 'border': 1})

        # === Sheet 1: Monthly Return ===
        ws = wb.add_worksheet('Monthly Tax Return')
        ws.set_column('A:A', 30)
        ws.set_column('B:B', 20)
        ws.merge_range('A1:B1', 'FBR MONTHLY SALES TAX RETURN', bold)
        ws.write('A2', f"Period: {self.date_from} to {self.date_to}", label)
        ws.write('A3', f"Company: {self.company_id.name}", label)
        ws.write('A5', 'Particulars', header)
        ws.write('B5', 'Amount (PKR)', header)
        ws.write('A6', 'Output GST (Sales Tax @ 18%)', label)
        ws.write('B6', self.output_tax, money)
        ws.write('A7', 'Input GST (Purchase Tax @ 18%)', label)
        ws.write('B7', self.input_tax, money)
        ws.write('A8', 'Net Tax Payable', label)
        ws.write('B8', self.net_tax_payable, total_fmt)

        # === Sheet 2: Sales Register ===
        ws2 = wb.add_worksheet('Sales Register')
        ws2.set_column('A:A', 14)
        ws2.set_column('B:B', 20)
        ws2.set_column('C:C', 25)
        ws2.set_column('D:D', 35)
        ws2.set_column('E:G', 18)
        cols = ['Date', 'Invoice No', 'Customer', 'Description', 'Taxable Amount', 'Tax', 'Total']
        for i, c in enumerate(cols):
            ws2.write(0, i, c, header)
        for r, row in enumerate(self._get_sales_data(), 1):
            ws2.write(r, 0, str(row['date']))
            ws2.write(r, 1, row['invoice_no'])
            ws2.write(r, 2, row['customer'])
            ws2.write(r, 3, row['description'])
            ws2.write(r, 4, row['taxable_amount'], money)
            ws2.write(r, 5, row['gst_amount'], money)
            ws2.write(r, 6, row['total'], money)

        # === Sheet 3: Purchase Register ===
        ws3 = wb.add_worksheet('Purchase Register')
        ws3.set_column('A:A', 14)
        ws3.set_column('B:B', 20)
        ws3.set_column('C:C', 25)
        ws3.set_column('D:F', 18)
        cols2 = ['Date', 'Invoice No', 'Supplier', 'Taxable Amount', 'Tax', 'Total']
        for i, c in enumerate(cols2):
            ws3.write(0, i, c, header)
        for r, row in enumerate(self._get_purchase_data(), 1):
            ws3.write(r, 0, str(row['date']))
            ws3.write(r, 1, row['invoice_no'])
            ws3.write(r, 2, row['supplier'])
            ws3.write(r, 3, row['taxable_amount'], money)
            ws3.write(r, 4, row['gst_amount'], money)
            ws3.write(r, 5, row['total'], money)

        wb.close()
        output.seek(0)
        xlsx_data = base64.b64encode(output.read()).decode()

        return self.env['ir.attachment'].create({
            'name': f'FBR_Tax_Return_{self.date_from}_{self.date_to}.xlsx',
            'datas': xlsx_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

    def action_export_xlsx(self):
        self.ensure_one()
        attachment = self._build_xlsx_attachment()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'download',
        }


class FbrTaxDashboard(models.Model):
    _name = 'fbr.tax.dashboard'
    _description = 'FBR Tax Dashboard'

    name = fields.Char(default='FBR Tax Dashboard')
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_dashboard_data', readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_dashboard_data', readonly=True)
    month = fields.Char(string='Month', compute='_compute_dashboard_data')
    total_sales = fields.Monetary(string='Total Sales', currency_field='currency_id', compute='_compute_dashboard_data')
    total_purchases = fields.Monetary(string='Total Purchases', currency_field='currency_id', compute='_compute_dashboard_data')
    output_tax = fields.Monetary(string='Output Tax', currency_field='currency_id', compute='_compute_dashboard_data')
    input_tax = fields.Monetary(string='Input Tax', currency_field='currency_id', compute='_compute_dashboard_data')
    net_tax_payable = fields.Monetary(string='Net GST Payable', currency_field='currency_id', compute='_compute_dashboard_data')

    def _compute_dashboard_data(self):
        for rec in self:
            dashboard_data = self.env['fbr.tax.report'].get_dashboard_data(company_id=self.env.company.id)
            rec.company_id = self.env.company
            rec.currency_id = self.env.company.currency_id
            rec.month = dashboard_data['month']
            rec.total_sales = dashboard_data['total_sales']
            rec.total_purchases = dashboard_data['total_purchases']
            rec.output_tax = dashboard_data['output_tax']
            rec.input_tax = dashboard_data['input_tax']
            rec.net_tax_payable = dashboard_data['net_tax_payable']
