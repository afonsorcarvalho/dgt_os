from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime


class DgtOsPecasLine(models.Model):
	_name = 'dgt_os.os.pecas.line'
	_description = u'Ordem de Serviço Peças Planejadas Line'
	_order = 'os_id, sequence, id'
	
	name = fields.Char('Descrição', size=64)
	os_id = fields.Many2one(
		'dgt_os.os', 'Repair Order Reference',
		index=True, ondelete='cascade')
	aplicada = fields.Boolean('Aplicada', copy=False)
	to_invoice = fields.Boolean('Faturar')
	product_id = fields.Many2one('product.product', u'Peças', required=True)
	invoiced = fields.Boolean('Faturada', copy=False, readonly=True)
	product_uom_qty = fields.Float(
		'Qtd', default=1.0,
		digits=dp.get_precision('Product Unit of Measure'), required=True)
	product_uom = fields.Many2one(
		'product.uom', 'Unidade de medida',
		required=True) 
	qty_available = fields.Float(
        'Quantity On Hand',compute = '_compute_peca_disponivel',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Current quantity of products.\n"
             "In a context with a single Stock Location, this includes "
             "goods stored at this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "stored in the Stock Location of the Warehouse of this Shop, "
             "or any of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.",readonly=True, copy=False)
	invoice_line_id = fields.Many2one(
		'account.invoice.line', 'Linha da fatura',
		copy=False, readonly=True)
	location_id = fields.Many2one(
		'stock.location', 'Origem',
		index=True, required=False)
	location_dest_id = fields.Many2one(
		'stock.location', 'Destino',
		index=True, required=False)
	move_id = fields.Many2one(
		'stock.move', 'Movimeto Estoque',
		copy=False, readonly=True)
	lot_id = fields.Many2one('stock.production.lot', 'Lote')
	sequence = fields.Integer(string='Sequence', default=10)
	
	@api.one
	@api.depends('product_uom_qty', 'product_id')
	def _compute_peca_disponivel(self):
		self.qty_available  = self.product_id.qty_available
  
		
	#@api.onchange('type', 'os_id')
	def onchange_operation_type(self):
		""" On change of operation type it sets source location, destination location
		and to invoice field.
		@param product: Changed operation type.
		@param guarantee_limit: Guarantee limit of current record.
		@return: Dictionary of values.
		"""
		if not self.type:
			self.location_id = False
			self.Location_dest_id = False
		elif self.type == 'add':
			args = self.os_id.company_id and [('company_id', '=', self.os_id.company_id.id)] or []
			warehouse = self.env['stock.warehouse'].search(args, limit=1)
			self.location_id = warehouse.lot_stock_id
			self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
			self.to_invoice = self.os_id.guarantee_limit and datetime.strptime(self.os_id.guarantee_limit, '%Y-%m-%d') < datetime.now()
		else:
			self.location_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
			self.location_dest_id = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id
			self.to_invoice = False
	
	@api.onchange('os_id', 'product_id', 'product_uom_qty')
	def onchange_product_id(self):
		""" On change of product it sets product quantity, tax account, name,
		uom of product, unit price and price subtotal. """
		args = self.os_id.company_id and [('company_id', '=', self.os_id.company_id.id)] or []
		warehouse = self.env['stock.warehouse'].search(args, limit=1)
		self.location_id = warehouse.lot_stock_id
		self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
	
		if self.product_id:
			self.name = self.product_id.display_name
			self.product_uom = self.product_id.uom_id.id
			self.qty_available = self.product_id.qty_available