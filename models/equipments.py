from odoo import models, fields, api


class Category(models.Model):
    _name = 'dgt_os.equipment.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Categoria de Equipamento'

    name = fields.Char()
    responsibles = fields.Many2many('res.users', string='Responsáveis')
    note = fields.Text()
    equipments_id = fields.One2many('dgt_os.equipment', 'category_id', string='Equipamentos')
    instructions_id = fields.One2many('dgt_os.equipment.category.instruction', 'category_id',copy=True)


class CategoryInstruction(models.Model):
    _name = 'dgt_os.equipment.category.instruction'

    name = fields.Char('Instrução')
    category_id = fields.Many2one('dgt_os.equipment.category')
    sequence = fields.Integer()


class MaintenanceTeam(models.Model):
    _name = 'dgt_os.equipment.maintenance.team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Equipe de Manutenção'

    name = fields.Char()
    team_members = fields.Many2many('hr.employee', string='Membros')


class Location(models.Model):
    _name = 'dgt_os.equipment.location'

    name = fields.Char('Local')


class Situation(models.Model):
    _name = 'dgt_os.equipment.situation'

    name = fields.Char('Situação')


class MeansOfAquisition(models.Model):
    _name = 'dgt_os.equipment.means.of.aquisition'

    name = fields.Char('Meio de Aquisição')


class Equipment(models.Model):
    _name = 'dgt_os.equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Equipamento'

    name = fields.Char()
    category_id = fields.Many2one('dgt_os.equipment.category', 'Categoria', required=True)
    client_id = fields.Many2one('res.partner', 'Cliente', required=True)
    situation_id = fields.Many2one('dgt_os.equipment.situation', 'Situação', required=True)
    means_of_aquisition_id = fields.Many2one('dgt_os.equipment.means.of.aquisition', 'Meio de Aquisição', required=True)
    technician_id = fields.Many2one('hr.employee', 'Técnico')
    maintenance_team_id = fields.Many2one('dgt_os.equipment.maintenance.team', 'Equipe de Manutenção')
    location_id = fields.Many2one('dgt_os.equipment.location', 'Local de Uso', required=True)
    partner_id = fields.Many2one('res.partner', 'Fornecedor')
    partner_reference = fields.Char('Referência de Fornecedor')
    model = fields.Char('Modelo')
    serial_number = fields.Char('Número de Série')
    anvisa_code = fields.Char('Reg Anvisa')
    tag = fields.Char('Tag')
    patrimony = fields.Char('Patrimonio')
    manufacturing_date = fields.Date('Data de Fabricação')
    instalation_date = fields.Date('Date de Instalação')
    acquisition_date = fields.Date('Date de Aquisição')
    warranty = fields.Date('Garantia')
    extended_warranty = fields.Date('Garantia Extendida')
    invoice_document = fields.Binary('Nota Fiscal')
    next_maintenance = fields.Date('Próxima Manutenção Preventiva')
    period = fields.Integer('Frequência de Manutenção')
    duration = fields.Float('Duração da Manutenção')
    note = fields.Text()

    _sql_constraints = [
		('serial_no_uniq', 
		'UNIQUE (serial_number)', 
		'Número de série deve ser único!') 
	]
    @api.multi
    def name_get(self):
                result = []
                for record in self:
                        if record.name and record.serial_number:
                                result.append((record.id, str(record.id) + '/' + record.name + '/' + record.serial_number))
                        if record.name and not record.serial_number:
                                result.append((record.id, record.name))
                return result
    

