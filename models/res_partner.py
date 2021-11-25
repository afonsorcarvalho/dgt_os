
from odoo import fields, models, api

class Partner(models.Model):
    """Modelo que adiciona a funcionalidade de auto preencher o cadastro no formulário de res.partner, em caso de pessoa juridica"""
    _inherit = 'res.partner'
    maintenance_email = fields.Char('Email Manutenção')
    allowed_payment_methods = fields.Many2many(
        'account.payment.term',
        string='Condições de Pagamento'
    )
    valor_diaria = fields.Float("Valor diária")
