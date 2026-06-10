{
    'name': 'FBR Sales Tax',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Sales Register, Purchase Register, Monthly Tax Return & Dashboard',
    'author': 'FBR Tax Plugin',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/fbr_tax_data.xml',
        'views/fbr_gst_calculator_views.xml',
        'views/fbr_dashboard_views.xml',
        'views/fbr_menu_views.xml',
        'report/fbr_sales_register_report.xml',
        'report/fbr_purchase_register_report.xml',
        'report/fbr_monthly_return_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fbr_sales_tax/static/src/css/fbr_dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
