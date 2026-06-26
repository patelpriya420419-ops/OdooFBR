from odoo import models, fields

class VatReportWizard(models.TransientModel):
    _name = 'vat.report.wizard'
    _description = 'Saudi VAT Report Wizard'

    amount = fields.Float(string='Amount (SAR)', required=True)

    def action_print_report(self):
        return self.env.ref('saudi_vat_report.action_saudi_vat_report').report_action(self)
