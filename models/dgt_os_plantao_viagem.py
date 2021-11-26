# -*- coding: utf-8 -*-
import time
from datetime import datetime,timedelta
from odoo import models, api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class DgtOsPlantaoViagem(models.Model):
	_name = 'dgt_os.os.plantao.viagem'
	_inherit = ['mail.thread']
	_description = u'Plantões e Viagens'
	_order = "data_inicio desc"

	_inherit = ['mail.thread', 'mail.activity.mixin',
                'portal.mixin', 'utm.mixin']


	state = fields.Selection(string='Status', selection=[
			('draft', 'Rascunho'),
			('em_aprovacao', 'Em Aprovação'),
			('aprovado', 'Aprovado'),
			('done', 'Concluído'),
			('cancelado', 'Cancelado'),
			
		],default='draft')
	
	name = fields.Char(string='RDV nº', required=True, copy=False,
                       readonly=True, index=True, default=lambda self: _('New'))
	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			if 'company_id' in vals:
				vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('dgt_os.os.plantao.viagem') or _('New')
			else:
				vals['name'] = self.env['ir.sequence'].next_by_code(
					'dgt_os.os.plantao.viagem') or _('New')
		
		result = super(DgtOsPlantaoViagem, self).create(vals)
		return result


	# name = fields.Char(
	# 	'Plantão Nº',default=lambda self: self.env['ir.sequence'].next_by_code('dgt_os.os.plantao.viagem'),
	# 	copy=False, required=True, 
		
	# 	)
	description = fields.Text('Descrição', required=True, 
		readonly=True, states={'draft': [('readonly', False)]} 
		
		)
	data_inicio = fields.Date('Data de início', track_visibility='onchange', default=fields.Date.context_today, required=True, 
		readonly=True, states={'draft': [('readonly', False)] } 
		
		)
	data_fim = fields.Date('Data de fim', track_visibility='onchange', required=True, 
		
		readonly=True, states={'draft': [('readonly', False)]} 
		
		
		)
	tipo = fields.Selection([('plantao', 'Plantão'),('viagem', 'Viagem')],
	required=True,
	readonly=True, states={'draft': [('readonly', False)]} 
		)
	tecnico_id = fields.Many2one('hr.employee', string="Técnico", domain=[("job_id", "=", "TECNICO")], required=True,
	readonly=True, states={'draft': [('readonly', False)]} )
	relatorios_id = fields.Many2many('dgt_os.os.relatorio.servico', string="Relatórios",
	readonly=True, states={'draft': [('readonly', False)]} 
		
		)
	despesas_line_id = fields.One2many('dgt_os.os.plantao.viagem.despesas.line', 'rdv_id',string ="despesas", 
	readonly=True, states={'draft': [('readonly', False)],'em_aprovacao':[('readonly', False)] } 
	
		
		)
	despesas_totais = fields.Float(
		string='Despesas Totais', 
		readonly=True,
		compute="_compute_despesas_totais", 
		store=True
		
		)
	
	@api.depends('despesas_line_id')
	def _compute_despesas_totais(self):
		for record in self:
			# fetch all records for your model and sum num field value
			sum_despesas = record._compute_sum_despesas_lines('valor')
			record.despesas_totais = sum_despesas
	
	
			

	adiantamentos = fields.Float(
		string='Adiantamentos',
		
		readonly=True ,
		compute="_compute_adiantamentos_total",
		store=True
		
		)

	@api.depends('despesas_line_id')
	def _compute_adiantamentos_total(self):
		for record in self:
			# fetch all records for your model and sum num field value
			sum_adiantamento = record._compute_sum_despesas_lines('valor_adiantamento')
			record.adiantamentos = sum_adiantamento
	
	despesas_aprovadas = fields.Float(
		string='Despesas aprovadas',
		
		readonly=True ,
		compute="_compute_despesas_aprovadas",
		store=True
		
		)

	@api.depends('despesas_line_id')
	def _compute_despesas_aprovadas(self):
		for record in self:
			# fetch all records for your model and sum num field value
			sum_despesas_aprovadas = record._compute_sum_despesas_lines('valor_aprovado')
			record.despesas_aprovadas = sum_despesas_aprovadas


			
	pagar_restituir = fields.Float(
		string='Restituir/pagar',
		readonly=True,
		compute = "_compute_pagar_restituir",
		store=True 
		
		)
	
	@api.depends('adiantamentos','despesas_totais')
	def _compute_pagar_restituir(self):
		for record in self:
			record.pagar_restituir = record.despesas_aprovadas - record.adiantamentos
	

	currency_id = fields.Many2one(string='Moeda', comodel_name='res.currency', ondelete='restrict')

	valor_total_diarias_a_pagar = fields.Monetary(string='Valor Diárias', currency_field='currency_id', 
		readonly=True,
		compute = "_compute_valor_total_diarias_a_pagar",
		store=True 
		)
	
	@api.depends('data_inicio','data_fim','tecnico_id','tipo')
	def _compute_valor_total_diarias_a_pagar(self):
		for record in self:
			
			if record.data_fim:
				_logger.info(record.data_fim - record.data_inicio)
				days_date = record.data_fim - record.data_inicio
				days = days_date.days
				_logger.info(self.tecnico_id.name)
				res_partner_tecnico = self.env['res.partner'].search([('name', '=', self.tecnico_id.name)], offset=0, limit=None, order=None, count=False)
				record.valor_total_diarias_a_pagar = days*res_partner_tecnico.valor_diaria
	
	def verify_relatorios(self):
		for record in self:
			if len(record.relatorios_id) > 0:
				return True
			return False

	def _compute_sum_despesas_lines(self,col_name_sum):
			sum_total = sum(self.env["dgt_os.os.plantao.viagem.despesas.line"].search([('rdv_id','=', self.id)]).mapped(col_name_sum))
			return sum_total
	
	def action_confirmar(self):
		
		for record in self:
			if record.tipo == 'plantao':
				record.set_state_em_aprovacao()
			else:
				if len(record.relatorios_id) > 0:
					record.set_state_em_aprovacao()
				else:
					raise UserError(
                	_('É necessário que tenha relatórios vinculados para o caso de viagens!  Vincule o relatório de serviço de acordo com a data de viagem'))

	def set_state_em_aprovacao(self):
		for record in self:
			for despesa in record.despesas_line_id:
				despesa.write({
					'state': 'em_aprovacao'
				})
			record.write({
					'state': 'em_aprovacao'
				})
	
	def action_provisorio(self):
		for record in self:
			record.write({
				'state': 'draft'
			})

	def action_aprovar(self):
		for record in self:
			record.write({
				'state': 'aprovado'
			})
	def action_cancelar(self):
		for record in self:
			record.write({
				'state': 'cancelado'
			})






class DgtOsPlantaoViagemDespesasLine(models.Model):
	_name = 'dgt_os.os.plantao.viagem.despesas.line'
	
	_description = u'Despesas Plantões e Viagens'
	_order = "data desc"

	state = fields.Selection(string='Status', selection=[
			('draft', 'Rascunho'),
			('em_aprovacao', 'Em Aprovação'),
			('aprovado', 'Aprovado'),
			('glozado', 'Glozado'),
		])

	name = fields.Char("Descrição", required=True)
	rdv_id = fields.Many2one(
		'dgt_os.os.plantao.viagem',
		"RDV",
		)
	data = fields.Date('Data', track_visibility='onchange', default=fields.Date.context_today, required=True, 
	 
	)
	valor = fields.Float("Valor", 
	required=True

	)
	valor_aprovado = fields.Float("Valor Aprovado", 
	)

	valor_adiantamento= fields.Float("Valor Adiantamento", 
	
	)
	
	observacoes = fields.Text("Observações", 
	
	)
	

	def action_aprovar(self):
		for record in self:
			record.write({
				'state': 'aprovado'
			})


	
	
	

