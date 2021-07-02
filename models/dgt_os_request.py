# -*- coding: utf-8 -*-
import time
from datetime import datetime,timedelta
from odoo import models, api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class DgtOsRequest(models.Model):
	_name = 'dgt_os.os.request'
	_inherit = ['mail.thread']
	_description = u'Solicitação de Serviço'
	_order = "id desc"

	@api.returns('self')
	def _default_stage(self):
		return self.env['maintenance.stage'].search([], limit=1)
	
	name = fields.Char(
		'Solicitação Nº',default=lambda self: self.env['ir.sequence'].next_by_code('dgt_os.os.request'),
		copy=False, required=True,readonly=True)
	description = fields.Text('Descrição', required=True)
	contact_os = fields.Char('Requisitante', required=True)
	request_date = fields.Date('Data da Solicitação', track_visibility='onchange', default=fields.Date.context_today)
	oss = fields.One2many(
		'dgt_os.os', 'request_id', 'Ordens de Serviço',
		copy=True, readonly=False, required=False) 
	cliente_id = fields.Many2one(
		'res.partner', 'Cliente',
		index=True, required=True,
		help='Escolha o cliente .')
	company_id = fields.Many2one(
		'res.company', 'Empresa',
		default=lambda self: self.env['res.company']._company_default_get('mrp.repair'))
	tecnicos = fields.Many2one('hr.employee', string="Técnico", domain=[("job_id", "=", "TECNICO")])
	equipments = fields.Many2many('dgt_os.equipment', string='Equipamentos', index=True)
	stage_id = fields.Selection([('new', 'Nova Solicitação'), ('in_progress', 'Em andamento'),('repaired', 'Reparado'), ('waste', 'Sucata')], default="new")
	priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Prioridade')
	color = fields.Integer('Color Index')
	close_date = fields.Date('Close Date')
	kanban_state = fields.Selection([('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
									string='Kanban State', required=True, default='normal', track_visibility='onchange')
	
	archive = fields.Boolean(default=False, help="Set archive to true to hide the maintenance request without deleting it.")
	maintenance_type = fields.Selection([('corrective', 'Corretiva'), ('preventive', 'Preventiva'),('instalacao','Instalação'),('treinamento','Treinamento')], required=True, string='Tipo de Manutenção', default="corrective")
	schedule_date = fields.Datetime('Data Programada',required=True)
	maintenance_team_id = fields.Many2one('dgt_os.equipment.maintenance.team', string='Equipe de Manutenção', required=True,)

	@api.multi
	def archive_equipment_request(self):
		self.write({'archive': True})

	@api.multi
	def reset_equipment_request(self):
		""" Reinsert the maintenance request into the maintenance pipe in the first stage"""
		first_stage_obj = self.env['maintenance.stage'].search([], order="sequence asc", limit=1)
		self.write({'archive': False, 'stage_id': first_stage_obj.id})

	@api.onchange('cliente_id')
	def onchange_cliente_id(self):
		"""Limpa o campo equipments quando o cliente for alterado"""
		self.equipments = ()				
	
	@api.multi
	def action_gera_os(self):
		args = self.company_id and [('company_id', '=', self.company_id.id)] or []
		warehouse = self.env['stock.warehouse'].search(args, limit=1)
		equipments = self.equipments
		
		for line in equipments:
			vals = {
					'origin': self.name,
					'cliente_id': self.cliente_id.id,
					'date_scheduled': self.schedule_date,
					'date_execution': self.schedule_date,
					'maintenance_type': self.maintenance_type,
					'description':self.description,
					'contact_os': self.contact_os,
					'equipment_id':line.id,
					'request_id':self.id,
					'priority':self.priority,
					'tecnicos_id': [(4, self.tecnicos.id)]
					}
			self.env['dgt_os.os'].create(vals)
			
		self.write({'stage_id': 'in_progress'})
		return True

	@api.multi
	def action_finish_request(self):
		if not self.oss.filtered(lambda os: os.state != 'done'):
			self.write({'stage_id': 'repaired'})
