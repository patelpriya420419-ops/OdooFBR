from odoo import models, fields, api


class FbrGstCalculator(models.TransientModel):
    _name = 'fbr.gst.calculator'
    _description = 'FBR GST Calculator'

    calc_mode = fields.Selection([
        ('exclusive', 'Amount Excluding GST → Calculate GST'),
        ('inclusive', 'Amount Including GST → Extract GST'),
    ], string='Calculation Mode', default='exclusive', required=True)

    input_amount = fields.Float(string='Enter Amount', required=True)
    gst_rate = fields.Float(string='GST Rate (%)', default=18.0, required=True)

    taxable_amount = fields.Float(string='Taxable Amount', compute='_compute_gst', store=False)
    gst_amount = fields.Float(string='GST Amount', compute='_compute_gst', store=False)
    total_amount = fields.Float(string='Total Amount (Incl. GST)', compute='_compute_gst', store=False)

    @api.depends('input_amount', 'gst_rate', 'calc_mode')
    def _compute_gst(self):
        for rec in self:
            rate = rec.gst_rate / 100.0
            if rec.calc_mode == 'exclusive':
                rec.taxable_amount = rec.input_amount
                rec.gst_amount = rec.input_amount * rate
                rec.total_amount = rec.input_amount * (1 + rate)
            else:
                rec.taxable_amount = rec.input_amount / (1 + rate)
                rec.gst_amount = rec.input_amount - rec.taxable_amount
                rec.total_amount = rec.input_amount
