import datetime
import time
from odoo.tests import common
from odoo import fields
from odoo.exceptions import UserError


class TestOsVerifyList(common.TransactionCase):
    def setUp(self):
        super(TestOsVerifyList, self).setUp()
        self.cliente = self.env["res.partner"].search([('name', '=', 'UNIFOR')])
        self.equipamento = self.env['maintenance.equipment'].search([('cliente_id.name', '=', 'UNIFOR')])
        self.tecnico = self.env['hr.employee'].search([('name', '=', 'ALYNE THAIANNE DE OLIVEIRA')])
        vals = {'name': 'OS. N 999', 'cliente_id': self.cliente.id, 'date_scheduled': time.strftime('%Y-%m-%d %H:%M:%S'), 'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'), 'maintenance_type': 'preventive', 'description':'Teste', 'equipment_id':self.equipamento.id, 'tecnicos_id': [(4, self.tecnico.id)]
		}
        self.os = self.env['dgt_os.os'].create(vals)

        self.os.action_repair_executar()
        
    def test_create_check_list(self):
        """Testa se a lista de verificacao é inserida na tabela os_verify_list quando o estado da os vai para to be invoiced e a os é do tipo preventiva"""
        
        self.assertEqual(self.os.state, 'under_repair')
        self.assertEqual(self.os.maintenance_type, 'preventive')
        self.assertEqual(len(self.os.check_list), 11)

    def test_create_check_list_only_for_preventive(self):
        """Testa se a lista de verificacao só é inserida na tabela os_verify_list quando o tipo de maintenance for igual a preventive"""
        cliente = self.env["res.partner"].search([('name', '=', 'UNIFOR')])
        equipamento = self.env['maintenance.equipment'].search([('cliente_id.name', '=', 'UNIFOR')])
        tecnico = self.env['hr.employee'].search([('name', '=', 'ALYNE THAIANNE DE OLIVEIRA')])
        vals = {
                    'name': 'OS. N 1000',
					'cliente_id': self.cliente.id,
					'date_scheduled': time.strftime('%Y-%m-%d %H:%M:%S'),
					'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
					'maintenance_type': 'corrective',
					'description':'Teste',
					'equipment_id':self.equipamento.id,
					'tecnicos_id': [(4, self.tecnico.id)]
		}
        os_corrective = self.env['dgt_os.os'].create(vals)

        os_corrective.action_repair_executar()

        self.assertEqual(len(os_corrective.check_list), 0)

    def test_instructions(self):
        """Testa se a instrucao de verificao é válida"""
        for i in self.os.check_list:
            self.assertNotEqual(False, i.instruction)


class TestDgtOs(common.TransactionCase):
    def setUp(self):
        super(TestDgtOs, self).setUp()
        self.cliente = self.env["res.partner"].search([('name', '=', 'UNIFOR')])
        self.equipamento = self.env['maintenance.equipment'].search([('cliente_id.name', '=', 'UNIFOR')])
        self.tecnico = self.env['hr.employee'].search([('name', '=', 'ALYNE THAIANNE DE OLIVEIRA')])
        vals = {
            'name': 'OS. N 999',
            'cliente_id': self.cliente.id,
            'date_scheduled': time.strftime('%Y-%m-%d %H:%M:%S'),
            'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
            'maintenance_type': 'preventive',
            'description':'Teste',
            'equipment_id':self.equipamento.id,
            'tecnicos_id': [(4, self.tecnico.id)]
            }
        self.os = self.env['dgt_os.os'].create(vals)
        self.relatorio = self.env['dgt_os.os.relatorio.servico'].create({'name': 'Teste', 'os_id': self.os.id, })
        self.relatorio_linha = self.env['dgt_os.os.relatorio.atendimento.line'].create(
            {'name': 'Teste Relatório Linha',
            'relatorio_id': self.relatorio.id, 
              })
        self.peca1 = self.env['product.product'].search([('name', '=', 'ABRACADEIRA NW 20/25')])
        self.peca2 = self.env['product.product'].search([('name', '=', 'ANEL GIRATORIO')])

        # Atualiza a quantidade no estoque
        self.atualizador_estoque = self.env['stock.quant']
        self.peca2.qty_available = 5.0

    def test_move_product_from_stock_when_client_has_a_location(self):
        """Testa se cria uma transferência de estoque quando o cliente possui um local cadastrado"""

        cliente = self.env["res.partner"].search([('name', '=', 'HMF - HOSPITAL DA MULHER')])
        equipamento = self.env['maintenance.equipment'].search([('id', '=', 21)])

        vals = {
            'cliente_id': cliente.id,
            'name': 'teste',
            'date_scheduled': time.strftime('%Y-%m-%d %H:%M:%S'),
            'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
            'maintenance_type': 'preventive',
            'description':'Teste',
            'equipment_id': equipamento.id,
            'tecnicos_id': [(4, self.tecnico.id)]
            }
        os = self.env['dgt_os.os'].create(vals)

        vals_peca = {'os_id': os.id, 'product_id': self.peca1.id, 'price_unit': self.peca1.list_price, 'product_uom': self.peca1.uom_id.id, 'aplicada': True} 
        os_pecas = self.env['dgt_os.os.pecas.line'].create(vals_peca)
        os_pecas.onchange_product_id()
        self.atualizador_estoque._update_available_quantity(self.peca1, os.location_id, 5)

        relatorio = self.env['dgt_os.os.relatorio.servico'].create({'name': 'Teste', 'os_id': os.id, })
        relatorio_linha = self.env['dgt_os.os.relatorio.atendimento.line'].create(
            {'name': 'Teste Relatório Linha',
            'relatorio_id': relatorio.id,
              })

        vals = {'os_id': self.os.id, 'product_id': self.peca1.id, 'price_unit': self.peca1.list_price, 'product_uom': self.peca1.uom_id.id, 'aplicada': True} 
        dgt_os_pecas = self.env['dgt_os.os.pecas.line'].create(vals)
        dgt_os_pecas.onchange_product_id()

        os.action_repair_executar()        
        
        self.assertEqual(os.pecas[0].qty_available, 5)
        self.assertEqual(os.state, "under_repair")

        os.action_repair_end()
    
        transferencia = self.env['stock.picking'].search([('origin', '=', os.name)])

        self.assertEqual(transferencia.origin, os.name)
        self.assertEqual(os.pecas.move_id.id, transferencia.move_lines.id)

    def test_not_move_product_from_stock_when_client_has_a_location_and_os_has_no_spare_part(self):
        """Testa se não cria uma transferência de estoque quando o cliente possui um local cadastrado e não tem nenhuma peça aplicada na OS"""

        cliente = self.env["res.partner"].search([('name', '=', 'HMF - HOSPITAL DA MULHER')])
        equipamento = self.env['maintenance.equipment'].search([('id', '=', 21)])

        vals = {
            'cliente_id': cliente.id,
            'name': 'teste',
            'date_scheduled': time.strftime('%Y-%m-%d %H:%M:%S'),
            'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
            'maintenance_type': 'preventive',
            'description':'Teste',
            'equipment_id': equipamento.id,
            'tecnicos_id': [(4, self.tecnico.id)]
            }
        os = self.env['dgt_os.os'].create(vals)

        relatorio = self.env['dgt_os.os.relatorio.servico'].create({'name': 'Teste', 'os_id': os.id, })
        relatorio_linha = self.env['dgt_os.os.relatorio.atendimento.line'].create(
            {'name': 'Teste Relatório Linha',
            'relatorio_id': relatorio.id,
              })

        os.action_repair_executar()
        
        self.assertEqual(os.state, "under_repair")

        os.action_repair_end()
    
        transferencia = self.env['stock.picking'].search([('origin', '=', os.name)])

        self.assertEqual(transferencia.origin, False)

    def test_os_change_to_state_released_when_there_is_no_replacement_part_in_inventory(self):
        vals = {'os_id': self.os.id, 'product_id': self.peca1.id, 'price_unit': self.peca1.list_price, 'product_uom': self.peca1.uom_id.id, 'aplicada': True} 
        dgt_os_pecas = self.env['dgt_os.os.pecas.line'].create(vals)
        dgt_os_pecas.onchange_product_id()
        self.os.action_repair_executar()
        self.assertEqual("released", self.os.state)
