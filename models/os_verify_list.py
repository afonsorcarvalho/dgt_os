from odoo import models, api, fields

class OsVerifyLis(models.Model):
    _name = 'dgt_os.os.verify.list'

    dgt_os = fields.Many2one('dgt_os.os', "OS")
    instruction = fields.Char('Instruções')
    check = fields.Boolean()
    observations = fields.Char()