# -*- coding: utf-8 -*-
{
    'name': 'Order Material',
    'version': '14.0.1',
    'author': 'Winston Curasi',
    'website': 'https://www.linkedin.com/in/winstoncurasi/',
    'summary': '',
    'description': "",
    'depends': [
        'stock', 'sale_management', 'purchase', 'product', 'contacts'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/order_material.xml',
        'wizard/message.xml',
        'reports/order_material.xml',
    ],
    'qweb': ['static/src/xml/stock.xml'],
    'application': True,
    'installable': True,
    'auto_install': False
}
