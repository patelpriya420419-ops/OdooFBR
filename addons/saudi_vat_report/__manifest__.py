{
    'name': 'Saudi VAT Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Saudi VAT 15% Calculation Report',
    'depends': ['base','web'],
    'data': [
        'security/ir.model.access.csv',
        'views/vat_report_wizard_views.xml',
        'report/report_action.xml',
        'report/vat_report_template.xml',
    ],
    'installable': True,
}