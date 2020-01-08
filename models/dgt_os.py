# -*- coding: utf-8 -*-
import time
from datetime import datetime,timedelta
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError
import logging


class DgtOs(models.Model):
	_name = 'dgt_os.os'
	_description = 'Ordem de Servico'
	_inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin','utm.mixin']
	_order = 'name'
	
	STATE_SELECTION = [
		('draft', 'Criada'),
		('cancel', 'Cancelada'),
		('under_repair', 'Em execução'),
		('done', 'Concluída'),
	]
	
	MAINTENANCE_TYPE_SELECTION = [
		('corrective', 'Corretiva'),
		('preventive', 'Preventiva'),
		('instalacao','Instalação'),
		('treinamento','Treinamento'),
		('preditiva','Preditiva'),
		('qualification', 'Qualificação'),
		('loan', 'Comodato'),
		('calibration', 'Calibração'),
	]
	
	@api.model
	def create(self, vals):
		"""Salva ou atualiza os dados no banco de dados"""
		if vals.get('name', _('New')) == _('New'):
			if 'company_id' in vals:
				vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('dgt_os.os') or _('New')
			else:
				vals['name'] = self.env['ir.sequence'].next_by_code('dgt_os.os') or _('New')

		result = super(DgtOs, self).create(vals)
		return result
				
	#@api.model
	#def _gera_qr(self):
     
	#	self.qr = self.name + "\n" + self.cliente_id.name + "\n" + self.equipment_id.name + "-" + self.equipment_id.serial_no
		
	@api.model
	def _default_journal(self):
		if self._context.get('default_journal_id', False):
			return self.env['account.journal'].browse(self._context.get('default_journal_id'))
		inv_type = self._context.get('type', 'out_invoice')
		inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
		company_id = self._context.get('company_id', self.env.user.company_id.id)
		domain = [
			('company_id', '=', company_id),
		]
		return self.env['account.journal'].search(domain, limit=1)
	@api.model
	def _default_currency(self):
		journal = self._default_journal()
		return journal.currency_id or journal.company_id.currency_id
		
	
	name = fields.Char(string='OS. N', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
	
	origin = fields.Char('Source Document', size=64, readonly=True, states={'draft': [('readonly', False)]},
		help="Referencia ao documento que gerou a ordem de servico.")
	state = fields.Selection(STATE_SELECTION, string='Status',
		copy=False, default='draft',  track_visibility='onchange',
		help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
			"* The \'Done\' status is set when repairing is completed.\n" 
			"* The \'Cancelled\' status is used when user cancel repair order.")
	kanban_state = fields.Selection([('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
									string='Kanban State', required=True, default='normal', track_visibility='onchange')
	location_id = fields.Many2one('stock.location', 'Estoque')
	priority = fields.Selection([('0','Normal'),('1',"Baixa"),('2',"Alta"),('3','Muito Alta')],'Prioridade',default='1')
	maintenance_type = fields.Selection(MAINTENANCE_TYPE_SELECTION, string='Tipo de Manutenção',required=True, default=None)
	time_execution = fields.Float("Tempo Execução", compute='_compute_time_execution', help="Tempo de execução em minutos",store=True)
	maintenance_duration = fields.Float("Tempo Estimado", related="equipment_id.duration", readonly=False)
	date_scheduled = fields.Datetime('Scheduled Date', required=True, default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
	date_execution = fields.Datetime('Execution Date', required=True, default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
	date_start = fields.Datetime('Início da Execução', default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
	currency_id = fields.Many2one('res.currency', string='Currency',
		readonly=True,
		default=_default_currency, track_visibility='always')
	request_id = fields.Many2one(
		'dgt_os.os.request', 'Solicitação Ref.',
		index=True, ondelete='restrict')
	problem_description = fields.Text('Descrição do Defeito')
	
	partner_invoice_id = fields.Many2one('res.partner', 'Fatura para')
	cliente_id = fields.Many2one(
		'res.partner', 'Cliente',
		index=True, required=True,
		help='Escolha o cliente que sera para fatura.')
	cliente_phone = fields.Char(
		'Telefone fixo do cliente',
		related='cliente_id.phone',
		readonly=True
	)
	cliente_cellphone = fields.Char(
		'Celular do cliente',
		related='cliente_id.mobile',
		readonly=True
	)
	cliente_email = fields.Char(
		'E-mail do cliente',
		related='cliente_id.email',
		readonly=True
	)
	cliente_email_manutencao = fields.Char(
		'E-mail do cliente para enviar as Ordens de Serviço',
		related='cliente_id.maintenance_email',
		readonly=True
	)
	cliente_cidade = fields.Char(
		'Cidade do cliente',
		related='cliente_id.city_id.name',
		readonly=True
	)
	cliente_estado = fields.Char(
		'Estado do cliente',
		related='cliente_id.state_id.name',
		readonly=True
	)
	cliente_rua = fields.Char(
		'Rua do cliente',
		related='cliente_id.street',
		readonly=True
	)
	cliente_numero = fields.Char(
		'Número do imóvel do cliente',
		related='cliente_id.number',
		readonly=True
	)
	contact_os = fields.Char(
		"Requisitante", size=60,
		help="Pessoa que solicitou a ordem de serviço",
		required=True,
	)
	
	picking_type = fields.Many2one(
		'stock.picking.type', 'Tipo de Recolha'
	)

	pecas = fields.One2many(
		'dgt_os.os.pecas.line', 'os_id', 'Pecas',
		copy=True,track_visibility='onchange')
		
	servicos = fields.One2many(
		'dgt_os.os.servicos.line', 'os_id', u'Serviços',
		copy=True, readonly=False,track_visibility='onchange')
	relatorios = fields.One2many(
		'dgt_os.os.relatorio.servico', 'os_id', u'Relatórios',
		copy=True, readonly=False,track_visibility='onchange')
	sale_id = fields.Many2one(
		'sale.order', 'Cotação',
		index=True, required=False,track_visibility='onchange',
		help='Escolha a cotação referente a OS.')
	invoice_id = fields.Many2one(
		'account.invoice', 'Fatura peças',
		copy=False,  track_visibility="onchange")
	invoice_servico_id = fields.Many2one(
		'account.invoice', 'Fatura Serviço',
		copy=False,  track_visibility="onchange")
	company_id = fields.Many2one(
		'res.company', 'Empresa',
		default=lambda self: self.env['res.company']._company_default_get('mrp.repair'))
	tecnicos_id = fields.Many2many(
		'hr.employee',string='Técnicos', required=True,track_visibility='onchange'
		)
	repaired = fields.Boolean(u'Concluído', copy=False, readonly=True)
	equipment_id = fields.Many2one(
		'dgt_os.equipment', 'Equipamento', 
		index=True, required=True,
		help='Escolha o equipamento referente a Ordem de Servico.'
		)
	description = fields.Text(required=True)
	procurement_group_id = fields.Many2one('procurement.group', 'Procurement group', copy=False)
	#qr = fields.Text('Qr code',compute='_gera_qr',readonly=True)
	account_analytic_id = fields.Many2one('account.analytic.account', string="Conta analítica")

	check_list = fields.One2many('dgt_os.os.verify.list', 'dgt_os',track_visibility='onchange')
	equipment_category = fields.Char(
		'Categoria do Equipamento',
		related='equipment_id.category_id.name',
		readonly=True
	)
	equipment_serial_number = fields.Char(
		'Número de Série do Equipamento',
		related='equipment_id.serial_number',
		readonly=True
	)
	equipment_model = fields.Char(
		'Modelo do equipamento',
		related='equipment_id.model',
		readonly=True
	)
	#equipment_location = fields.Many2one(
	#	'Localizacao do equipamento',
	#	related='equipment_id.location_id',
	#	readonly=True
	#)
	equipment_tag = fields.Char(
		'Tag do Equipamento',
		related='equipment_id.tag',
		readonly=True
	)
	equipment_patrimonio = fields.Char(
		'Patrimonio do Equipamento',
		related='equipment_id.patrimony',
		readonly=True
	)
		
	@api.multi
	@api.depends('relatorios')
	def _compute_time_execution(self):
		if self.relatorios:
			tempo = 0.0
			for rel in self.relatorios:
				tempo += rel.time_execution
			self.update({'time_execution' : tempo})
	
	@api.onchange('cliente_id')
	def onchange_client_id(self):
		if self.cliente_id:
			self.equipment_id = ()

	@api.onchange('date_scheduled')
	def onchange_scheduled_date(self):
		self.date_execution = self.date_scheduled

	@api.onchange('date_execution')
	def onchange_execution_date(self):
		if self.state == 'draft':
			self.date_planned = self.date_execution
		else:
			self.date_scheduled = self.date_execution

	@api.onchange('tecnicos_id')
	def onchange_tecnicos_id(self):
		location_ref = self.env['stock.location']
		if self.tecnicos_id:
			tecnico = self.tecnicos_id[0]
			location_id = location_ref.search([('partner_id.name', '=', tecnico.name)])
			if location_id:
				self.location_id = location_id.id

	@api.onchange('location_id')
	def onchange_location_id(self):
		picking_ref = self.env['stock.picking.type']
		company_id = self._context.get('company_id', self.env.user.company_id.id)
		if self.location_id and self.location_id.partner_id.id != company_id:
			location = self.location_id.id
			picking_type = picking_ref.search([('default_location_src_id', '=', self.location_id.id)])
			self.picking_type = picking_type.id
			
	@api.multi
	def action_draft(self):
		return self.action_repair_cancel_draft()
		
	@api.multi
	def action_repair_cancel_draft(self):
		if self.filtered(lambda dgt_os: dgt_os.state != 'cancel'):
			raise UserError(_("Repair must be canceled in order to reset it to draft."))
		self.mapped('pecas').write({'state': 'draft'})
		return self.write({'state': 'draft'})
	
	@api.multi
	def action_repair_executar(self):
		if self.filtered(lambda dgt_os: dgt_os.state == 'done'):
			raise UserError(_("O.S já concluída."))
		if self.filtered(lambda dgt_os: dgt_os.state == 'under_repair'):
			raise UserError(_('O.S. já em execução.'))

		self.create_checklist()
		self.message_post(body='Iniciada execução da ordem de serviço!')
		return self.write({'state': 'under_repair', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
			
	@api.multi
	def action_repair_cancel(self):
		self.mapped('pecas').write({'state': 'cancel'})
		return self.write({'state': 'cancel'})
	
	@api.multi
	def action_repair_start(self):
		""" Writes repair order state to 'Under Repair'
		@return: True
		"""
		if self.filtered(lambda dgt_os: dgt_os.state not in ['confirmed', 'ready']):
			raise UserError(_("Repair must be confirmed before starting reparation."))
		self.mapped('pecas').write({'state': 'confirmed'})
		return self.write({'state': 'under_repair'})
		
					
	@api.multi
	def action_repair_end(self):
		""" Writes repair order state to 'To be invoiced' if invoice method is
		After repair else state is set to 'Ready'.
		@return: True
		"""
		if self.filtered(lambda dgt_os: dgt_os.state != 'under_repair'):
			raise UserError(_("A ordem de serviço de estar \"em execução\" para finalizar a execução."))

		if self.filtered(lambda dgt_os: dgt_os.state == 'done'):
			raise UserError(_('Ordem já finalizada'))

		if not self.relatorios:	
			raise UserError(_("Para finalizar O.S. deve-se incluir pelo menos um relatório de serviço."))
			return False

		vals = {
				'state': 'done',
				'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
		}
		#self.action_repair_done()
		self.write(vals)
		self.request_id.action_finish_request()
		
		self.write({'repaired': True})
		return True
		
	@api.multi
	def action_repair_done(self):
		""" Creates stock move for operation and stock move for final product of repair order.
		@return: Move ids of final products
		"""
		if self.filtered(lambda dgt_os: not dgt_os.repaired):
			raise UserError(_("Repair must be repaired in order to make the product moves."))

		if self.pecas:
			location_ref = self.env['stock.location']
			location_dest_id = location_ref.search([('partner_id.name', '=', self.cliente_id.name)])
			if location_dest_id.partner_id:
				
				stock_picking = self.env['stock.picking'].create({'origin': self.name,
				'move_type': 'one',
				'location_id': self.location_id.id,
				'location_dest_id': location_dest_id.id,
				'picking_type_id': self.picking_type.id,
				'partner_id': self.cliente_id.id})

				movimento = self.env['stock.move']
				for dgt_os in self:
					for operation in dgt_os.pecas:
						move = movimento.create({
							'name': operation.name,
							'product_id': operation.product_id.id,
							'restrict_lot_id': operation.lot_id.id,
							'product_uom_qty': operation.product_uom_qty,
							'product_uom': operation.product_uom.id,
							'partner_id': dgt_os.cliente_id.id,
							'location_id': self.location_id.id,
							'location_dest_id': location_dest_id.id,
							'picking_id': stock_picking.id,
							'quantity_done': operation.product_uom_qty
						})
						operation.write({'move_id': move.id, 'state': 'done'})	
	
	def create_checklist(self):
		"""Cria a lista de verificacao caso a os seja preventiva"""
		if self.maintenance_type == 'preventive' or self.maintenance_type == 'loan' or self.maintenance_type == 'calibration':
			instructions = self.env['maintenance.equipment.category.vl'].search([('category_id.name', '=', self.equipment_id.category_id.name)])
			os_check_list = self.env['dgt_os.os.verify.list']

			for i in instructions:
				os_check_list.create({'dgt_os': self.id, 'instruction': str(i.name)})

class ServicosLine(models.Model):
	_name = 'dgt_os.os.servicos.line'
	_description = 'Servicos Line'
	_order = 'os_id, sequence, id'
	
	name = fields.Char('Description', required=True)
	os_id = fields.Many2one(
		'dgt_os.os', 'Ordem de Serviço',
		index=True, ondelete='cascade')
	to_invoice = fields.Boolean('Faturar')
	product_id = fields.Many2one('product.product', u'Serviço',domain=[('type','=','service')], required=True)
	invoiced = fields.Boolean('Faturada', copy=False, readonly=True)
	tax_id = fields.Many2many(
		'account.tax', 'dgt_os_service_line_tax', 'dgt_os_service_line_id', 'tax_id', 'Impostos')
	product_uom_qty = fields.Float(
		'Qtd', default=1.0,
		digits=dp.get_precision('Product Unit of Measure'), required=True)
	product_uom = fields.Many2one(
		'product.uom', 'Unidade de medida',
		required=True)
	invoice_line_id = fields.Many2one(
		'account.invoice.line', 'Linha da fatura',
		copy=False, readonly=True)
	sequence = fields.Integer(string='Sequence', default=10)
	
	@api.onchange('os_id', 'product_id', 'product_uom_qty')
	def onchange_product_id(self): 
		""" On change of product it sets product quantity, tax account, name,
		uom of product, unit price and price subtotal. """
		if self.product_id:
			self.name = self.product_id.display_name
			self.product_uom = self.product_id.uom_id.id
			
			
class RelatoriosServico(models.Model):
	_name = 'dgt_os.os.relatorio.servico'	
	_inherit = ['mail.thread']
	name = fields.Char(
		'Nº Relatório de Serviço',default=lambda self: self.env['ir.sequence'].next_by_code('dgt_os.os.relatorio'),
		copy=False, required=True)
	os_id = fields.Many2one(
		'dgt_os.os', 'Ordem de serviço',
		index=True, ondelete='cascade')
	cliente_id = fields.Many2one('res.partner', string='Owner',
		compute='_compute_relatorio_default',
		track_visibility='onchange',store=True)
	relatorio_num = fields.Char('Nº Relatório')
	data_atendimento = fields.Date('Data atendimento', required=True)
	hora_inicio = fields.Float('Hora de início', required=True)
	hora_termino = fields.Float('Hora de termino', required=True)
	equipment_id = fields.Many2one(
		'dgt_os.equipment','Equipamento',
		compute='_compute_relatorio_default',
		store=True,
		index=True,
		help='Escolha o equipamento referente ao Relatorio de Servico.')
	tecnicos_id = fields.Many2many(
		'hr.employee',	
		string = 'Técnicos')
	motivo_chamado = fields.Text('Descreva o motivo do chamado')
	defeitos = fields.Text('Descreva tecnicamente o defeito apresentado')
	servico_executados = fields.Text('Descreva o serviço realizado')
	pendencias = fields.Text('Descreva pendências')
	atendimentos = fields.One2many(
		'dgt_os.os.relatorio.atendimento.line', 'relatorio_id', 'Atendimento',
		 readonly=False)
	time_execution = fields.Float(String='tempo execução',compute='_compute_time_execution', store=True )
 
 	#@api.multi
  	#def get_data_hora_inicio(self):
    #   self.search([('', '=', ), ...], offset=0, limit=None, order=None, count=False)
    #   result = self.search([('dgt_os','=', self.os_id.id)], order="data_atendimento ASC, hora_inicio ASC",limit=1)
    #   data = result.data_atendimento + result.hora_inicio
       
		
  
  
	@api.multi
	@api.depends('hora_inicio', 'hora_termino')
	def _compute_time_execution(self):
		for rel in self:
			tempo = rel.hora_termino - rel.hora_inicio
			self.update({ 'time_execution' : tempo})		
			
	@api.one
	@api.depends('os_id','os_id.cliente_id','os_id.equipment_id')
	def _compute_relatorio_default(self):
		self.cliente_id = self.os_id.cliente_id.id
		self.equipment_id = self.os_id.equipment_id.id
		

class RelatoriosAtendimentoLines(models.Model):
	#TODO remover esse model e fazer a migração dos dados
	_name = "dgt_os.os.relatorio.atendimento.line"
	
	name = fields.Char('Item',readonly=True)
	relatorio_id = fields.Many2one(
		'dgt_os.os.relatorio.servico', 'Repair Order Reference',
		index=True,  ondelete='cascade')
	data_ini = fields.Datetime(string='Data de Início', 
		help='Data de inicio do servico')
	data_fim = fields.Datetime(string='Data de Fim',
		help='Data de fim do servico')
		
	@api.constrains('data_fim')
	def constrains_data_fim(self):
		data_fim = datetime.strptime(self.data_fim, "%Y-%m-%d %H:%M:%S")
		data_ini = datetime.strptime(self.data_ini, "%Y-%m-%d %H:%M:%S")
		if data_fim.date() < data_ini.date():
			raise UserError(_("Dia do final do relatório menor que o dia do inicio."))
		elif data_fim.date() == data_ini.date(): 
			if data_fim.time() < data_ini.time():
				raise UserError(_("Hora da data de final do relatório menor que a hora da data de inicio."))
