# -*- coding: utf-8 -*-
{
    'name': "Ordem de Serviço",
	'version': '1.0',
    'sequence': 200,
    'category': 'AT',
    'summary': 'Gerenciamento de Assistência Técnica',

    'summary': """
        Módulo de gerenciamento de assistência técnica com solicitação de serviço e ordem de serviço
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Engº Afonso Carvalho",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
   
    # any module necessary for this one to work correctly
    'depends': [
        'br_base',
        'br_sale',
        'stock',
        'web_digital_sign',
        'sale_management',
        'sale_commission' ,
        'br_product',
        'account',
        'br_account',
        'mail',
        'utm',
        'portal',
        'web', 
        'hr'
    ],

    # always loaded 
    'data': [
		'security/at_security.xml',
	    'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'wizard/relatorio_os.xml',
        'views/sale_view.xml',
		'views/dgt_os_pecas_line_view.xml',
		'views/dgt_os_view.xml',
		'views/dgt_os_request_view.xml',
        'views/dgt_os_os_relatorio_servico_view.xml',
        'views/dgt_os_form_view.xml',
        'views/dgt_os_plantao_viagem.xml',
        'views/equipment_view.xml',
        'views/equipment_category_view.xml',
        'views/maintenance_team_view.xml',
        'views/menu_items.xml',
        'views/product_category.xml',
        
	    'reports/reports.xml',
       	'reports/report_base_ordem.xml',
	    'reports/report_ordem_servico.xml',
	    'reports/report_orcamento_servico.xml',
        'views/base_view_partner_form.xml',
        'reports/sale_report_views.xml',
        'email_template/dgt_os_email_template.xml',
		'data/ir_sequence_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
	'installable': True,
    'auto_install': False,
    'application': True,
}
