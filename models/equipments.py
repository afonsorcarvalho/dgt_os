from odoo import models, fields, api


class Equipment(models.Model):
    _name = 'dgt_os.equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Equipamento'

    name = fields.Char()
    category_id = fields.Many2one(
        'dgt_os.equipment.category', 'Categoria', required=True)
    client_id = fields.Many2one('res.partner', 'Cliente', required=True)
    situation_id = fields.Many2one(
        'dgt_os.equipment.situation', 'Situação', required=True)
    means_of_aquisition_id = fields.Many2one(
        'dgt_os.equipment.means.of.aquisition', 'Meio de Aquisição', required=True)
    technician_id = fields.Many2one('hr.employee', 'Técnico')
    maintenance_team_id = fields.Many2one(
        'dgt_os.equipment.maintenance.team', 'Equipe de Manutenção')
    location_id = fields.Many2one(
        'dgt_os.equipment.location', 'Local de Uso', required=True)
    partner_id = fields.Many2one('res.partner', 'Fornecedor')
    partner_reference = fields.Char('Referência de Fornecedor')
    model = fields.Char('Modelo', 
    required=True
    )
    serial_number = fields.Char('Número de Série', copy=False)
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
    oses = fields.One2many(
        string='Ordens de serviço',
        comodel_name='dgt_os.os',
        inverse_name='equipment_id',
        
        store=False,
    )
    relatorios = fields.One2many(
        'dgt_os.os.relatorio.servico', 'equipment_id', u'Relatórios',
        copy=True, readonly=False, track_visibility='onchange')
    
    _sql_constraints = [
        ('serial_no_uniq',
         'UNIQUE (serial_number,partner_id)',
         'Número de série para cada fabricante deve ser único!')
    ]

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.name and record.serial_number:
                result.append((record.id, str(record.id) + '/' +
                               record.name + '/' + record.serial_number))
            if record.name and not record.serial_number:
                result.append((record.id, record.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []

        if operator == 'ilike' and not (name or '').strip():
            recs = self.search([] + args, limit=limit)
        elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
            recs = self.search(['|', '|', ('name', operator, name), (
                'id', operator, name), ('serial_number', operator, name)] + args, limit=limit)

        return recs.name_get()


class Category(models.Model):
    _name = 'dgt_os.equipment.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Categoria de Equipamento'

    name = fields.Char()
    responsibles = fields.Many2many('res.users', string='Responsáveis')
    note = fields.Text()
    equipments_id = fields.One2many(
        'dgt_os.equipment', 'category_id', string='Equipamentos')
    instructions_id = fields.One2many(
        'dgt_os.equipment.category.instruction', 'category_id', copy=True)
    sequence = fields.Integer(string='Sequence', default=10)


class CategoryInstruction(models.Model):
    _name = 'dgt_os.equipment.category.instruction'

    name = fields.Char('Instrução')
    category_id = fields.Many2one('dgt_os.equipment.category')
    sequence = fields.Integer(string='Sequence', default=10)


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
    _sql_constraints = [

        ('situation_uniq', 'unique (name)', 'O nome já existe !')

    ]


class MeansOfAquisition(models.Model):
    _name = 'dgt_os.equipment.means.of.aquisition'

    name = fields.Char('Meio de Aquisição')

   

