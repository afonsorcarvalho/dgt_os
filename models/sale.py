from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class DgtSaleOrder(models.Model):
    _inherit = 'sale.order'

    os_id = fields.Many2one('dgt_os.os', string='Ordem de serviço',copy=False)
    
    @api.multi
    def action_confirm(self):
        _logger.debug("Confirmando venda")
        _logger.debug("Ordem de serviço %s", self.os_id.name)
        res = super(DgtSaleOrder, self).action_confirm()
        _logger.debug(res)
        
        if self.os_id.id:
            _logger.debug("Ordem de serviço %s sendo aprovada", self.os_id.name)
            self.os_id.approve()
        return res
    