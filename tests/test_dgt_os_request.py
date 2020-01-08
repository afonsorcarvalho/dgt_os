import datetime
from odoo.tests import common
from odoo import fields


class TestRequest(common.TransactionCase):

    def setUp(self):
        super(TestRequest, self).setUp()
        self.solicitante = self.env['res.users'].search([('name', '=', 'ALYNE')])
        self.cliente = self.env['res.partner'].search([('name', '=', 'UNIFOR')])
        self.equipamento = self.env['maintenance.equipment'].search([('name', '=', 'UNIFOR - LAVADORA TERMODESINFECTORA')])
        self.tecnico = self.env['hr.employee'].search([('name', '=', 'ALYNE THAIANNE DE OLIVEIRA')])
        # self.teste_solicitacao = self.env['dgt_os.os.request'].create({
        #     'name': 'SS/2018/999',
        #     'tecnicos': self.tecnico.id,
        #     'cliente_id': self.cliente.id,
        #     'equipments': self.equipamento.id,
        #     'maintenance_type': 'corrective',
        #     'schedule_date': fields.Date.today()
        # })

    def test_gerar_os(self):
        """Teste que verifica se é possível gerar uma os por meio de uma solicitação de serviço"""
        
        self.assertEqual(self.cliente.name, 'UNIFOR')
        self.assertEqual(self.tecnico.name, 'ALYNE THAIANNE DE OLIVEIRA')
        self.assertEqual(self.equipamento.name, 'UNIFOR - LAVADORA TERMODESINFECTORA')
        # self.assertEqual(self.teste_solicitacao.name, 'SS/2018/999')