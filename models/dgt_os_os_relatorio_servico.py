
import time
from datetime import date, datetime, timedelta
from odoo import models, fields, api, _, SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)

class RelatoriosServico(models.Model):
    _name = 'dgt_os.os.relatorio.servico'
    _inherit = ['mail.thread']
    _order = 'data_atendimento'

    date_now = fields.datetime.now()
    name = fields.Char(
        'Nº Relatório de Serviço', default=lambda self: self.env['ir.sequence'].next_by_code('dgt_os.os.relatorio'),
        copy=False, required=True)
    state = fields.Selection(string='Status', selection=[(
        'draft', 'rascunho'), ('done', 'Concluído')], default='draft')
    type_report = fields.Selection(string='Tipo de Relatório', selection=[(
        'quotation', 'Orçamento'), ('repair', 'Manutenção'),('instalation', 'Instalação'), ('calibrate', 'Calibração')], default="repair")
    parts_request = fields.One2many(
        'dgt_os.os.pecas.line', 'relatorio_request_id', 'Pecas Requisitadas',
        copy=True)
    parts_application = fields.One2many(
        'dgt_os.os.pecas.aplication.line', 'relatorio_aplication_id', 'Pecas Aplicadas',
        copy=True)
    os_id = fields.Many2one(
        'dgt_os.os', 'Ordem de serviço',
        index=True, ondelete='cascade')
    cliente_id = fields.Many2one('res.partner', string='Owner',
                                 compute='_compute_relatorio_default',
                                 track_visibility='onchange', store=True)
    observations = fields.Char(string='Observações')

    relatorio_num = fields.Char('Nº Relatório')
    data_atendimento = fields.Date(
        'Data atendimento', required=True, default=fields.date.today())
    hora_inicio = fields.Float('Hora de início', default=float(
        fields.datetime.now().hour) + float(fields.datetime.now().minute)/60, required=True)
    hora_termino = fields.Float('Hora de termino', default=float(fields.datetime.now(
    ).hour + 1) + float(fields.datetime.now().minute)/60, required=True)
    equipment_id = fields.Many2one(
        'dgt_os.equipment', 'Equipamento',
        compute='_compute_relatorio_default',
        store=True,
        index=True,
        
    
        
        help='Escolha o equipamento referente ao Relatorio de Servico.')
    situation_id = fields.Many2one(
        'dgt_os.equipment.situation',
        string='Estado do Equipamento',
        required=True
        
        )
    tecnicos_id = fields.Many2many(
        'hr.employee',
        string='Técnicos')
    motivo_chamado = fields.Text('Descreva o motivo do chamado')
    tem_defeitos = fields.Boolean(string='tem defeitos?', default=False)
    defeitos = fields.Text('Descreva tecnicamente o defeito apresentado')
    servico_executados = fields.Text('Descreva o serviço realizado')
    tem_pendencias = fields.Boolean('Tem pendencias?', default=False)
    pendencias = fields.Text('Descreva pendências')

    # atendimentos = fields.One2many(
    #	'dgt_os.os.relatorio.atendimento.line', 'relatorio_id', 'Atendimento',
    #	 readonly=False)
    time_execution = fields.Float(
        String='tempo execução', compute='_compute_time_execution', store=True)
    
    maintenance_duration = fields.Float(
        "Tempo Estimado",
        readonly=False,
        
        help='Tempo estimado que será utilizado para contabilizar o valor da mão de obra no orçamento'
        
        )

    # assinatura digital
    name_digital_signature_client = fields.Char(
        string=u'Nome do Cliente Assinatura',
    )
    
    signature_client_date = fields.Datetime(string="Data Assinatura do Cliente", default=time.strftime(
        '%Y-%m-%d %H:%M:%S'), track_visibility='onchange')
    
    is_sign_client = fields.Boolean(
        string='Assinado pelo cliente', 
        default=False
       
    )

    document_digital_signature_client = fields.Char(
        string=u'Documento do Cliente Assinatura',
    )

    type_document_signature_client = fields.Selection(string=u"Tipo de Documento",selection=[('rg', 'RG'),('cpf','CPF'),('matricula','Matrícula'),('Outros','Outros')])




    digital_signature_client = fields.Binary(string='Assinatura Cliente')
   
    def set_is_sign_client(self):
        self.is_sign_client = 1
    
  

    
    
    
 
    
    
    
    # @api.multi
    # def get_data_hora_inicio(self):
    #   self.search([('', '=', ), ...], offset=0, limit=None, order=None, count=False)
    #   result = self.search([('dgt_os','=', self.os_id.id)], order="data_atendimento ASC, hora_inicio ASC",limit=1)
    #   data = result.data_atendimento + result.hora_inicio

    @api.multi
    @api.depends('hora_inicio', 'hora_termino')
    def _compute_time_execution(self):
        for rel in self:
            tempo = rel.hora_termino - rel.hora_inicio
            self.update({'time_execution': tempo})

    @api.one
    @api.depends('os_id', 'os_id.cliente_id', 'os_id.equipment_id', 'os_id.tecnicos_id', 'os_id.description')
    def _compute_relatorio_default(self):
        self.cliente_id = self.os_id.cliente_id.id
        self.equipment_id = self.os_id.equipment_id.id
        self.tecnicos_id = self.os_id.tecnicos_id
        self.motivo_chamado = self.os_id.description
        if self.os_id.state == 'under_budget':
            self.servico_executados = 'Realizado Orçamento'
    


    @api.multi
    def aplicar_pecas(self):
        _logger.debug("APLICANDO PEÇAS")
        pecas_aplicadas = self.parts_application
        for peca in pecas_aplicadas:
            peca.parts_request.write({'aplicada':True})
            _logger.debug(peca.parts_request.id)
            _logger.debug(peca.parts_request.aplicada)



    @api.multi
    def action_done(self):
        
        _logger.debug("CONCLUINDO RELATORIO")
        self.aplicar_pecas()
        self.write({'state': 'done'})
        return
    
    @api.multi
    def action_atualizar(self):
        _logger.debug("ATUALIZANDO RELATORIO")




class RelatoriosAtendimentoLines(models.Model):
    # TODO remover esse model e fazer a migração dos dados
    _name = "dgt_os.os.relatorio.atendimento.line"

    name = fields.Char('Item', readonly=True)

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
            raise UserError(
                _("Dia do final do relatório menor que o dia do inicio."))
        elif data_fim.date() == data_ini.date():
            if data_fim.time() < data_ini.time():
                raise UserError(
                    _("Hora da data de final do relatório menor que a hora da data de inicio."))

    @api.model
    def create(self, values):
        result = super().create(values)
        _logger.debug("CRIANDO RELATÓRIO")
        return result

   
    
class PecasAplicationLine(models.Model):

    _name = 'dgt_os.os.pecas.aplication.line'
    parts_request = fields.Many2one(
        'dgt_os.os.pecas.line', 'Pecas Aplicadas',
        copy=True)
    relatorio_aplication_id = fields.Many2one(
        'dgt_os.os.relatorio.servico',
        string='RAT Aplicado',
        )
    os_id = fields.Many2one(
        'dgt_os.os', 'Ordem de serviço',
        index=True, ondelete='cascade')

    _sql_constraints = [

        ('parts_uniq', 'unique (parts_request)', 'A mesma peça foi aplicada mais de uma vez !')

    ]