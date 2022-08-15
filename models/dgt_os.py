import time
from datetime import date, datetime, timedelta
from odoo import models, fields,  api, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DgtOs(models.Model):
    _name = 'dgt_os.os'
    _description = 'Ordem de Serviço'
    _inherit = ['mail.thread', 'mail.activity.mixin',
                'portal.mixin', 'utm.mixin']
    _order = 'name'

    STATE_SELECTION = [
        ('draft', 'Criada'),
        ('under_budget', 'Em Orçamento'),
        ('pause_budget', 'Orçamento Pausado'),
        ('wait_authorization', 'Esperando aprovação'),
        ('wait_parts', 'Esperando peças'),
        ('execution_ready', 'Pronta para Execução'),
        ('under_repair', 'Em execução'),
        ('pause_repair', 'Execução Pausada'),
        ('reproved','Reprovada'),
        ('done', 'Concluída'),
        ('cancel', 'Cancelada'),
    ]

    # TODO Transformar o tipo de manutenção em uma classe
    MAINTENANCE_TYPE_SELECTION = [
        ('corrective', 'Corretiva'),
        ('preventive', 'Preventiva'),
        ('instalacao', 'Instalação'),
        ('treinamento', 'Treinamento'),
        ('preditiva', 'Preditiva'),
        ('qualification', 'Qualificação'),
        ('loan', 'Comodato'),
        ('calibration', 'Calibração'),

    ]

    GARANTIA_SELECTION = [
        ('proprio', 'Próprio'),
        ('fabrica', 'Fábrica')
    ]

    @api.model
    def open_sales(self):
        _logger.debug("Open sale clicado")

    @api.model
    def create(self, vals):
        """Salva ou atualiza os dados no banco de dados"""
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(
                    force_company=vals['company_id']).next_by_code('dgt_os.os') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'dgt_os.os') or _('New')

        result = super(DgtOs, self).create(vals)
        return result

    # @api.model
    # def _gera_qr(self):

    #	self.qr = self.name + "\n" + self.cliente_id.name + "\n" + self.equipment_id.name + "-" + self.equipment_id.serial_no

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get(
            'company_id', self.env.user.company_id.id)
        domain = [
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='OS. N', required=True, copy=False,
                       readonly=True, index=True, default=lambda self: _('New'))
    
    company_id = fields.Many2one(
        string='Empresa', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )

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
    priority = fields.Selection([('0', 'Normal'), ('1', "Baixa"),
                                 ('2', "Alta"), ('3', 'Muito Alta')], 'Prioridade', default='1')
    maintenance_type = fields.Selection(
        MAINTENANCE_TYPE_SELECTION, string='Tipo de Manutenção', required=True, default=None)
    time_execution = fields.Float(
        "Tempo Execução", compute='_compute_time_execution', help="Tempo de execução em minutos", store=True)
    maintenance_duration = fields.Float(
        "Tempo Estimado", default='1.0', readonly=False)
    is_warranty = fields.Boolean(string="É garantia",  default=False)
    warranty_type = fields.Selection(
        string='Tipo de Garantia', selection=GARANTIA_SELECTION)
    date_scheduled = fields.Datetime('Scheduled Date', required=True, default=time.strftime(
        '%Y-%m-%d %H:%M:%S'), track_visibility='onchange')
    date_execution = fields.Datetime('Execution Date', required=True, default=time.strftime(
        '%Y-%m-%d %H:%M:%S'), track_visibility='onchange')
    date_start = fields.Datetime('Início da Execução', default=time.strftime(
        '%Y-%m-%d %H:%M:%S'), track_visibility='onchange')
    data_start_quotation = fields.Datetime(
        'Início do orçamento', track_visibility='onchange', help='Data e hora do início do orçamento')
    data_stop_quotation = fields.Datetime(
        'Fim do orçamento', track_visibility='onchange', help="Data de fim do orçamento")
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
   # cliente_email_manutencao = fields.Char(
   #     'E-mail do cliente para enviar as Ordens de Serviço',
   #     related='cliente_id.maintenance_email',
   #     readonly=True
   # )
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
        copy=True, track_visibility='onchange')

    servicos = fields.One2many(
        'dgt_os.os.servicos.line', 'os_id', u'Serviços',
        copy=True, readonly=False, track_visibility='onchange')
    relatorios = fields.One2many(
        'dgt_os.os.relatorio.servico', 'os_id', u'Relatórios',
        copy=True, readonly=False, track_visibility='onchange')
    

        

    sale_id = fields.Many2one(
        'sale.order', 'Cotação',
        index=True, required=False, track_visibility='onchange',
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
        'hr.employee', string='Técnicos', required=True, track_visibility='onchange'
    )

    repaired = fields.Boolean(u'Concluído', copy=False, readonly=True)

    equipment_id = fields.Many2one(
        'dgt_os.equipment', 'Equipamento',
        index=True, required=True,
        help='Escolha o equipamento referente a Ordem de Servico.'
    )
    equipment_location = fields.Many2one(
        string='Setor de Uso', related='equipment_id.location_id', store=True)
    description = fields.Text(
        required=True, help="Descrição do serviço realizado ou a ser relalizado")
    procurement_group_id = fields.Many2one(
        'procurement.group', 'Procurement group', copy=False)
    #qr = fields.Text('Qr code',compute='_gera_qr',readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string="Conta analítica", )
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Posição Fiscal',  required=False, help='Posição fiscal para faturamento')
    check_list = fields.One2many(
        'dgt_os.os.verify.list', 'dgt_os', track_visibility='onchange')
    check_list_created = fields.Boolean(
        'Check List Created', track_visibility='onchange', default=False)
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
    # equipment_location = fields.Many2one(
    #	'Localizacao do equipamento',
    #	related='equipment_id.location_id',
    #	readonly=True
    # )
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
    # assinatura digital
    name_digital_signature_client = fields.Char(
        string=u'Nome do Cliente Assinatura',
    )
    signature_client_date = fields.Datetime(string="Data Assinatura do Cliente", default=time.strftime(
        '%Y-%m-%d %H:%M:%S'), track_visibility='onchange')
    sign_client = fields.Boolean(
        string='Assinado pelo cliente'
    )

    doc_digital_signature_client = fields.Char(
        string=u'Documento do Cliente Assinatura',
    )

    digital_signature_client = fields.Binary(string='Assinatura Cliente')
    gerado_cotacao = fields.Boolean(
        string=u'Cotação gerada?',
    )

    picture_ids = fields.One2many('dgt_os.os.pictures', 'os_id', "fotos")

    def set_sign_client(self):
        self.sign_client = 1

    @api.multi
    @api.depends('relatorios')
    def _compute_time_execution(self):
        if self.relatorios:
            tempo = 0.0
            for rel in self.relatorios:
                tempo += rel.time_execution
            self.update({'time_execution': tempo})

    #******************************************
    #  ONCHANGES
    #
    #******************************************


    @api.onchange('cliente_id')
    def onchange_client_id(self):
        if self.cliente_id:
            self.equipment_id = ()
        self.fiscal_position_id = self.cliente_id.property_account_position_id.id

    @api.onchange('date_scheduled')
    def onchange_scheduled_date(self):
        self.date_execution = self.date_scheduled

    @api.onchange('digital_signature_client')
    def onchange_digital_signature_client(self):
        self.signature_client_date = time.strftime('%Y-%m-%d %H:%M:%S')
        self.set_sign_client()

    @api.onchange('date_execution')
    def onchange_execution_date(self):
        if self.state == 'draft':
            self.date_planned = self.date_execution
        else:
            self.date_scheduled = self.date_execution

    @api.onchange('maintenance_duration')
    def onchange_maintenance_duration(self):
        _logger.debug("maintenance_duration mudado")
        _logger.debug("Ordem de serviço %s", self.name)
        rec = self.servicos
        for r in rec:
            _logger.debug("Serviços %s", r.name)
            if r.automatic:
                _logger.debug("Este foi colocado automaticamente")
                _logger.debug("Mudando a quantidade para %s",
                              self.maintenance_duration)
                r.product_uom_qty = self.maintenance_duration
            else:
                _logger.warning("Nenhum serviço adicionado automaticamente")

    @api.onchange('tecnicos_id')
    def onchange_tecnicos_id(self):
        _logger.debug(self.tecnicos_id)
        list_tecnicos_name = []
        for tecnico in self.tecnicos_id:
            list_tecnicos_name.append(tecnico.name)
        str_tecnicos = ", "
        str_tecnicos = str_tecnicos.join(list_tecnicos_name)
        body = "Modificado Tecnicos -> " + str_tecnicos
        # self.message_post(body=body)
        location_ref = self.env['stock.location']
        if len(self.tecnicos_id) > 0:
            tecnico = self.tecnicos_id[0]
            location_id = location_ref.search(
                [('partner_id.name', '=', tecnico.name)])
            if location_id:
                self.location_id = location_id.id

    @api.onchange('location_id')
    def onchange_location_id(self):
        picking_ref = self.env['stock.picking.type']
        company_id = self._context.get(
            'company_id', self.env.user.company_id.id)
        if self.location_id and self.location_id.partner_id.id != company_id:
            location = self.location_id.id
            picking_type = picking_ref.search(
                [('default_location_src_id', '=', self.location_id.id)])
            self.picking_type = picking_type.id
    
    @api.onchange('relatorios')
    def onchange_relatorios(self):
        _logger.debug('Onchange Relatórios')
        #self.update_parts_os()
    
    @api.multi
    def verify_on_add_relatorios(self):
        _logger.debug('INICIANDO CRIAÇÃO DE RELATÓRIOS')
        return True
    
    """
        function que atualiza as peças que foram requisitada no relatório nas pecas da OS
    """
    @api.multi
    def update_parts_os(self):
        _logger.info("Atualizando pecas requisitadas na os")
        #for os in self:
        _logger.info("OS")
        _logger.info(self)
        _logger.info("PROCURANDO RELATORIOS")
        _logger.info(self.relatorios)
        for relatorio in self.relatorios:

                parts_request = relatorio.parts_request
                _logger.debug("Atualizando Pecas Requisitadas na OS")
                _logger.debug(parts_request)

                for parts in parts_request:
                    _logger.debug(parts.parts_request.display_name)
                    pecas_line = self.env['dgt_os.os.pecas.line'].search([('relatorio_parts_id', '=', parts.id)])
                    _logger.debug(pecas_line)
                    if len(pecas_line) == 0:
                        _logger.debug("Ainda não foi adicionada a peça do relatorio na OS")
                        _logger.debug(pecas_line)
                        _logger.debug(self.name)
                        vals = {              
                            'os_id': self.id,
                            'name': parts.parts_request.display_name,
                            'relatorio_parts_id': parts.id,
                            'product_id': parts.parts_request.id,
                            'product_uom_qty': parts.product_uom_qty,
                            'product_uom': parts.parts_request.uom_id.id,
                            'relatorio_request_id': relatorio.id,
                        }
                        self.pecas = [(0,0,vals)]
                    else:
                        _logger.debug("Peca já adicionada!!!")
                        _logger.debug(pecas_line.name)
                        _logger.debug(pecas_line)
                        
                        
                    
                        
                    
                    
            


    def verify_execution_rules(self):
        """ Verifica as regras para início da execução da OS
        
        """
        if self.filtered(lambda dgt_os: dgt_os.state == 'done'):
            raise UserError(_("O.S já concluída."))
        if self.filtered(lambda dgt_os: dgt_os.state == 'under_repair'):
            raise UserError(_('O.S. já em execução.'))
        return

  
    #******************************************
    #  ACTIONS
    #
    #******************************************
    @api.multi
    def action_draft(self):
        return self.action_repair_cancel_draft()

    @api.multi
    def action_repair_cancel_draft(self):
        if self.filtered(lambda dgt_os: dgt_os.state != 'cancel'):
            raise UserError(
                _("Repair must be canceled in order to reset it to draft."))
        self.mapped('pecas').write({'state': 'draft'})
        return self.write({'state': 'draft'})

    @api.multi
    def action_repair_pause(self):
        if self.filtered(lambda dgt_os: dgt_os.state != 'under_repair'):
            raise UserError(
                _("Repair must be canceled in order to reset it to draft."))

        return self.write({'state': 'pause_repair'})

    def relatorio_service_start(self, type_report):
        tecnicos_id = self.tecnicos_id
        motivo_chamado = ''
        servicos_executados = ''
        tem_pendencias = False
        pendencias=''

        if type_report == 'quotation':
            motivo_chamado = 'Realizar Orçamento'
            servicos_executados = 'Orçamento'
            tem_pendencias = True
            pendencias = 'Aprovação do orçamento'



        else:
            if self.maintenance_type == 'preventive':
                motivo_chamado = 'Realizar manutenção preventiva'
                servicos_executados = 'Realizado Check-list de manutenção Preventiva'
            if self.maintenance_type == 'instalacao':
                motivo_chamado = 'Realizar Instalação'
                servicos_executados = 'Realizado procedimentos e Check-list de instalação'
            if self.maintenance_type == 'treinamento':
                motivo_chamado = 'Realizar treinamento'
                servicos_executados = 'Realizado treinamento operacional'
            if self.maintenance_type == 'calibration':
                motivo_chamado = 'Realizar Calibração'
                servicos_executados = 'Realizado calibração conforme procedimentos padrão'
            if self.maintenance_type == 'corrective':
                motivo_chamado = self.description
                servicos_executados = ''
        self.env['dgt_os.os.relatorio.servico'].create({
            'os_id': self.id,
            'type_report': type_report,
            'cliente_id': self.cliente_id.id,
            'equipment_id': self.equipment_id.id,
            'tecnicos_id': tecnicos_id,
            'motivo_chamado': motivo_chamado,
            'servico_executados': servicos_executados,
            'tem_pendencias': tem_pendencias,
            'pendencias': pendencias,
            'maintenance_duration': 1

        })
    
     # apenas usado para teste de pegar o representante com suas comissões
    # TODO
    # apagar essa action após desenvolvimento
    #
    @api.multi
    def action_agente(self):
        self.set_agente_commission()

    @api.multi
    def action_quotation_start(self):
        self.message_post(body='Iniciada orçamento da ordem de serviço!')
        if(self.maintenance_type == 'corrective'):
            self.verify_others_os_open()

        self.quotation_relatorio_service_start()
        _logger.debug("Iniciando Orçamento")
        res = self.write(
            {'state': 'under_budget', 'date_start_quotation': time.strftime('%Y-%m-%d %H:%M:%S')})
        self.add_service()
        return res

    def verify_others_os_open(self):
        domain = ['&',
            ('maintenance_type', '=', 'corrective'),
            ('equipment_id', '=', self.equipment_id.id),
            ('state', '!=', 'draft'),
            ('state', '!=', 'cancel'),
            ('state', '!=', 'done'),
            ('state', '!=', 'reproved'),
            ('state', '!=', 'wait_authorization'),
            ('state', '!=', 'wait_parts'),
            ('id', '!=', self.id),
        ]
        result = self.env['dgt_os.os'].search(domain)
        _logger.debug("Verificando outras OSES")
        _logger.debug(result)
        message_oses = 'Não é possível executar ação. Já existe(m) OS(s) para manutenção corretiva aberta desse equipamento:\n '
        
        for res in result:
            message_oses += res.name + '\n'
        
        if len(result) > 0:
            raise UserError(message_oses)

        
    @api.multi
    def action_quotation_pause(self):
        self.message_post(body='Pausado orçamento da ordem de serviço!')
        self.quotation_relatorio_service_end()
        res = self.write({'state': 'pause_budget'})
        return res

    #TODOProcurar se é contrato com peças e o orçamento ser autorizado automaticamente.
    @api.multi
    def action_quotation_end(self):
        self.message_post(body='Finalizado orçamento da ordem de serviço!')
        self.quotation_relatorio_service_end()
        self.gera_orcamento()
        
        res = self.write({'state': 'wait_authorization'})
        return res

    @api.multi
    def action_repair_aprove(self):
        self.message_post(body='Aprovado orçamento da ordem de serviço!')
        if self.state != 'done':
            res = self.write({'state': 'execution_ready'})
        return res
    
    @api.multi
    def action_repair_reprove(self):
        self.message_post(body='Reprovado o orçamento da ordem de serviço!')
        if self.state != 'reproved':
            res = self.write({'state': 'reproved'})
        return res
    @api.multi
    def action_wait_parts(self):
        self.message_post(body='Esperando peças chegar no estoque!')
        res = self.write({'state': 'wait_parts'})
        return res

    @api.multi
    def action_repair_executar(self):

        self.verify_execution_rules()
        self.repair_relatorio_service_start()
        if self.state == 'draft' or self.state == 'execution_ready':
            _logger.debug("Criando Check List")
            self.create_checklist()
        self.message_post(body='Iniciada execução da ordem de serviço!')
        res = self.write(
            {'state': 'under_repair', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    @api.multi
    def action_pause_repair_executar(self):

        self.verify_execution_rules()
        self.create_checklist()
        self.message_post(body='Pausada execução da ordem de serviço!')
        res = self.write(
            {'state': 'under_repair', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    @api.multi
    def action_repair_cancel(self):
        self.mapped('pecas').write({'state': 'cancel'})
        return self.write({'state': 'cancel'})

    @api.multi
    def action_repair_end(self):
        """Finaliza execução da ordem de serviço.

        @return: True
        """

        if self.filtered(lambda dgt_os: dgt_os.state != 'under_repair'):
            raise UserError(
                _("A ordem de serviço de estar \"em execução\" para finalizar a execução."))

        if self.filtered(lambda dgt_os: dgt_os.state == 'done'):
            raise UserError(_('Ordem já finalizada'))

        if not self.relatorios:
            raise UserError(
                _("Para finalizar O.S. deve-se incluir pelo menos um relatório de serviço."))
            return False
        if self.relatorios.filtered(lambda x: x.state == 'draft'):
            raise UserError(
                _("Para finalizar O.S. deve-se concluir todos os relatorios de serviço."))
            return False
           

        # verificando se pecas foram aplicadas
        for p in self.pecas:
            if not p.aplicada:
                raise UserError(
                    _("Para finalizar O.S. todas as peças devem ser aplicadas"))
                return False
        # if self.check_list_created:
        for check in self.check_list:
            if not check.check:
                raise UserError(
                    _("Para finalizar O.S. todas as instruções do check-list devem estar concluídas"))
                return False

        vals = {
            'state': 'done',
            'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        # self.action_repair_done()
        res = self.write(vals)
        if res:
            if self.sale_id.id:
                _logger.debug("Cotação já foi gerada: %s", self.sale_id.name)
            else:
                _logger.debug("Cotação ainda não gerada. Gerando...")
                self.gera_orcamento()

            if self.request_id.id:
                self.request_id.action_finish_request()
                _logger.debug("Concluída Solicitação")
            else:
                _logger.debug("Não existe solicitação para OS. Continuando...")
            _logger.debug("Finalizando relatorios.")
            self.finish_report()
            return True
        else:
            _logger.debug("Erro ao atualizar OS.")
            return False

    def repair_relatorio_service_start(self):
        date_now = datetime.now()
        type_report = 'repair'
        self.relatorio_service_start(type_report)

    def quotation_relatorio_service_start(self):
        date_now = datetime.now()
        type_report = 'quotation'
        self.relatorio_service_start(type_report)

    def quotation_relatorio_service_end(self):
        type_report = 'quotation'
        relatorio_servico = self.env['dgt_os.os.relatorio.servico'].search(
            [('os_id', '=', self.id), ('type_report', '=', type_report), ('state', '=', 'draft')])
        _logger.info("RELATORIOS DE SERVIÇOS ACHADOS")
        _logger.info(relatorio_servico)

        if len(relatorio_servico) > 0:
            raise UserError(
                    _("Antes de finalizar você precisa concluir relatório de orçamento. "))
        self.update_parts_os()
                            
    def set_agente_commission(self):
        _logger.debug("pegando agente comissão")

        for tec in self.tecnicos_id:
            rec = self.env['res.partner'].search(
                [('name', '=', tec.name)], offset=0, limit=None, order=None, count=False)
            if len(rec) <= 0:
                raise UserError(
                    _("Não foi encontrado nenhum técnico para comissionar. "))
            if rec.id:
                _logger.debug(
                    "Achado tecnico nome: %s, partner name: %s", tec.name, rec.name)
                if rec.agent:
                    _logger.debug("Técnico é representante")
                    _logger.debug("Tipo de representante: %s", rec.agent_type)
                    _logger.debug("Comissão é %s", rec.commission.name)
                    _logger.debug("Tipo de comissãp é %s",
                                  rec.commission.commission_type)
                    _logger.debug("Porcentagem é %s", rec.commission.fix_qty)
                    _logger.debug("Pegando a cotaçaõ ")
                    _logger.debug("Cotação %s", self.sale_id)

                    for item_sale in self.sale_id.order_line:
                        _logger.debug("item %s", item_sale.name)
                        _logger.debug("procurando comissão")
                        if len(item_sale.agents):
                            for item_agents in item_sale.agents:
                                _logger.debug(
                                    "O representante do item é  %s", item_agents.agent.name)
                                _logger.debug("Nome da comissão  %s",
                                              item_agents.agent.commission.name)
                                _logger.debug(
                                    "Valor da comissão  %s", item_agents.amount)
                        else:
                            _logger.debug("Nenhuma comissão colocada  ")
                            _logger.debug("Tipo de order line  %s",
                                          item_sale.display_type)
                            if item_sale.display_type == 'line_section' or item_sale.display_type == 'line_note':
                                _logger.debug(
                                    "Esta linha não se coloca representante")
                            else:

                                _logger.debug(
                                    "Adicionando representante da comissão %s", rec.agent_type)
                                _logger.debug("Comission %s",
                                              rec.commission.id)

                                res = item_sale.write({
                                    'agents': [(0, 0, {
                                        'agent': rec.id,
                                        'commission': rec.commission.id
                                    }
                                    )]
                                }

                                )
                                _logger.debug("salvo comissão, resultado:")
                                _logger.debug(res)
                else:
                    _logger.debug("tecnico não é representante")
            else:
                _logger.debug(
                    "Não foi achado tecnico nome: %s, partner name: %s", tec.name, rec.name)

    @api.multi
    def finish_report(self):
        _logger.debug("Procurando relatorios...")
        if self.relatorios:
            for rec in self.relatorios:
                rec.state = 'done'
        return True

    # utilizado na venda para atorizar Ordem de serviço
    @api.multi
    def approve(self):
        _logger.debug("Mudando state da os %s", self.name)
        for item in self:
            if item.state != 'done':
                item.write({'state': 'execution_ready'})
                post_vars = {'subject': "Ordem Aprovada",
                            'body': "A cotação foi aprovada pelo cliente, favor agendar execução",
                           } # Where "4" adds the ID to the list 
                                       # of followers and "3" is the partner ID 
                
                item.message_post(body="A cotação foi aprovada pelo cliente, favor agendar execução",subject="Ordem Aprovada",partner_ids=[3])
        _logger.debug("os state=%s ", self.state)

    # TODO
    #  - Colocar também o técnico que irá receber a comissão
    #  - colocar tempo de execução no serviço do contrato, mas isso tem que ser feito ao realizar fim da execução ou qd
    #   aciona o botão de gerar o orçamento
    #  - fazer atualização do orçamento ao mudar alguma coisa de peças e serviços na Ordem de serviço
    #
    def gera_orcamento(self):
        self.sudo()
        if self.filtered(lambda dgt_os: dgt_os.gerado_cotacao == True):
            raise UserError(
                _("Cotação para esse Ordem de serviço já foi gerada"))

        if not len(self.servicos):
            raise UserError(
                _("Para gerar cotação deve ter pelo menos um serviço adicionado"))

        if self.state == 'under_budget':
            _logger.debug("Ordem de serviço em orçamento")
            _logger.debug("Procura serviço para atualizar tempo")

        _logger.debug("Posicão Fiscal: %s", self.fiscal_position_id.name)
        _logger.debug("Conta Analítica: %s", self.analytic_account_id.name)
        _logger.debug("Gerando cotação para %s:", self.name)

        # criando cotação
        saleorder = self.env['sale.order'].create({
            "origin": self.name,
            "partner_id": self.cliente_id.id,
            "os_id": self.id,
            "analytic_account_id": self.analytic_account_id.id,
            "fiscal_position_id": self.fiscal_position_id.id,

        })

        _logger.info("Sale_order gerada: %s", saleorder.name)
        _logger.debug(saleorder)

        # erro na geração da cotação
        if not saleorder.id:
            raise UserError(
                _("Algum erro inesperado na geração da cotação. Cotação não gerada!!"))
        
        # cotação gerada com sucesso
        else:
           
            _logger.debug("criar linhas da sale.order:")
            _logger.debug(saleorder.name)

            # adicionando notas
            self.add_notes_orcamento(saleorder)
         
            # adicionando peças
            self.add_pecas_orcamento(saleorder)  

            # adicionando serviços
            _logger.debug("Adicionando seção de serviços:")
            self.add_servico_orcamento(saleorder)
            
            # sinalizando que cotação ja foi gerada
            self.write({'sale_id': saleorder.id, 'gerado_cotacao': True})

            # adicionando comissão ao agente
            self.set_agente_commission()

        return True

    def add_notes_orcamento(self, saleorder):
        """ Adiciona os notes ao orçamento da OS
            @param saleorder cotação a qual será adicionada os notes
        
        
        ."""
        # Adicionandos notas
        
        name_note = "Referente ao Ordem de Serviço "
        name_note = name_note + "nº " + self.display_name + " do Equipamento "
        if self.equipment_id.name:
            name_note = name_note + self.equipment_id.name
        #if self.equipment_id.category_id.name: name_note = name_note + self.equipment_id.category_id.name
        if self.equipment_serial_number:
            name_note = name_note + " NS " + \
                str(self.equipment_serial_number)
        if self.equipment_model:
            name_note = name_note + " Modelo: " + str(self.equipment_model)
        

        _logger.debug(
                "Adicionando notas explicativas da cotação: %s", name_note)

        self.env['sale.order.line'].create({
                'name': name_note,
                'display_type': 'line_note',
                'order_id': saleorder.id,
                'product_id': False,
                'product_uom': False,

            })

    def add_pecas_orcamento(self, saleorder):
        """ Adiciona pecas ao orçamento da OS
            @param saleorder cotação a qual será adicionada o notes
        
        
        ."""
        # Adicionando as peças

        # Verificando se tem pecas para adicionar
        if len(self.pecas) == 0:
            _logger.debug("Nenhuma peça para adicionar!!")
        else:
            secao_str = "Peças da " + self.name + ":"
            _logger.debug("Adicionando seção peça da cotação: %s", secao_str)
            
            self.env['sale.order.line'].create({
                'name': secao_str,
                'display_type': 'line_section',
                'order_id': saleorder.id,
                'product_id': False,
                'product_uom': False,

            })
            _logger.debug("Sessão criada!!!")
            _logger.debug("Adicionando linhas de pecas:")
            for peca in self.pecas:

                saleline = self.env['sale.order.line'].sudo().create({

                    'order_id': saleorder.id,
                    'product_id': peca.product_id.id,
                    'product_uom_qty': peca.product_uom_qty,
                    'product_uom': peca.product_uom.id,
                    'invoice_lines': peca.invoice_line_id.id,
                })
                _logger.debug("Adicionado peça %s, qty %s",
                                saleline.product_id.name, saleline.product_uom_qty)
    
    def add_servico_orcamento(self, saleorder):
        """ Adiciona serviços ao orçamento da OS
            @param saleorder cotação a qual será adicionada o serviço
        
        
        ."""
        # Adicionando Servicos

        self.env['sale.order.line'].create({
                'name': "Serviços da " + self.name + ":",
                'display_type': 'line_section',
                'order_id': saleorder.id,
                'product_id': False,
                'product_uom': False,

            })
        _logger.debug("Sessão serviços criada!!!")

        # TODO Pegar do contrato o serviço product_id caso tenha configurado no contrato
        for servico in self.servicos:
            _logger.info("adicionando linhas:")
            saleline = self.env['sale.order.line'].sudo().create({

                'order_id': saleorder.id,
                'product_id': servico.product_id.id,
                'product_uom_qty': servico.product_uom_qty,
                'product_uom': servico.product_uom.id,
                'invoice_lines': servico.invoice_line_id.id,
            })
            _logger.debug("Adicionado serviço %s, qty %s",
                            saleline.product_id.name, saleline.product_uom_qty)

    

    def add_service(self):
        """
            Adiciona serviço de acordo com a OS
            Verifica se equipamento em garantia, serviço em contrato e coloca o serviço adequado
        """
        _logger.debug("adicionando serviço...")
        _logger.debug(self.contrato) 
        _logger.debug("procurando serviço já adicionados na OS")

        added_services = self.env['dgt_os.os.servicos.line'].search([('os_id', '=',self.id )], offset=0, limit=None, order=None, count=False)
        servicos_line = []

        _logger.debug("Serviços achados para OS")
        for serv_line in added_services: 
            servicos_line.append(serv_line.product_id)
            _logger.debug(serv_line.product_id.name)
        
          
        _logger.debug("Serviços Padrão")
        service_default = self.env['product.product'].search([('name','ilike','Manutenção Geral')], limit=1)
        _logger.debug(service_default.name)
    
        if not service_default.id:
            raise UserError(_("Serviço padrão não configurado. Favor configurá-lo. Adicione o serviço 'Manutenção Geral'"))
        product_id = service_default
        
            
        if self.contrato.id:
            _logger.debug("Mudando serviço pois existe contrato para esse equipamento:")
            _logger.debug("Colocando serviço padrão para contrato:")
            if self.contrato.service_product_id.id:
                #verificando se tem esse serviço ja foi adicionado
                if self.contrato.service_product_id in servicos_line:
                    _logger.debug("Já existe serviço adicionado: %s", self.contrato.service_product_id.name)
                else:
                    _logger.debug("Serviço adicionado: %s", self.contrato.service_product_id.name)
                    product_id = self.contrato.service_product_id
        if self.is_warranty:
            if self.warranty_type == "fabrica":
                _logger.debug("Serviço em garantia fabrica")
                service_warranty = self.env['product.product'].search([('name','ilike','Serviço em garantia de fábrica')], limit=1)
                if not service_warranty.id:
                    raise UserError(_("Serviço garantia não configurado. Favor configurá-lo. Adicione o serviço 'Serviço em garantia de fábrica'"))
                
            else:
                _logger.debug("Serviço em garantia própria")
                service_warranty = self.env['product.product'].search([('name','ilike','Serviço em garantia')], limit=1)
                if not service_warranty.id:
                    raise UserError(_("Serviço garantia não configurado. Favor configurá-lo. Adicione o serviço 'Serviço em garantia'"))

            product_id= service_warranty
            
        _logger.debug("Verificando tempo para adicionar no serviço")
        if self.time_execution > 0:
            _logger.debug("Colocado tempo de execução no serviço: %s",self.time_execution )
            product_uom_qty = self.time_execution
            
        else:
            _logger.debug("Colocado tempo estimado no serviço: %s", self.maintenance_duration)
            product_uom_qty = self.maintenance_duration
        _logger.debug("Create servicos line:")

        if self.description:
            name = self.description
        else:
            name = product_id.display_name

        if len(servicos_line) == 0:
            _logger.debug("Serviços sera adicionado")
            self.servicos = [(0,0,{
                    'os_id' : self.id,
                    'automatic': True,
                    'name': name,
                    'product_id' : product_id.id,
                    'product_uom': product_id.uom_id.id,
                    'product_uom_qty' : product_uom_qty
                })]
            _logger.debug( self.servicos)
        else: 
            _logger.debug("Serviços sera apenas atualizado")
            for servico in added_services:
             
                if servico.automatic:
                    _logger.debug("Encontrado servicos adicionados automaticamente, atualizando")
                    self.servicos = [(1,servico.id,{
                            'os_id' : self.id,
                            'automatic': True,
                            'name': name,
                            'product_id' : product_id.id,
                            'product_uom': product_id.uom_id.id,
                            'product_uom_qty' : product_uom_qty
                        })]

     

                
        return self.servicos
   

    def create_checklist(self):
        """Cria a lista de verificacao caso a os seja preventiva."""
        if self.maintenance_type == 'preventive' or self.maintenance_type == 'loan' or self.maintenance_type == 'calibration':
            _logger.debug("Criando Checklist")
            instructions = self.env['maintenance.equipment.category.vl'].search(
                [('category_id.name', '=', self.equipment_id.category_id.name)])
            os_check_list = self.env['dgt_os.os.verify.list'].search(
                [('category_id.name', '=', self.equipment_id.category_id.name)])

            for i in instructions:
                instructions = os_check_list.create(
                    {'dgt_os': self.id, 'instruction': str(i.name)})
                _logger.debug(i)

            self.check_list_created = True

class OsPictures(models.Model):
    _name = 'dgt_os.os.pictures'
    _description = "Fotos do atendimento"

    name = fields.Char('Título da foto')
    description = fields.Text('Descrição da foto')

    
    os_id = fields.Many2one(
        string='Os', 
        comodel_name='dgt_os.os', 
        required=True, 
       
    )

    picture = fields.Binary(string="Foto", 
    required=True
     )
class ServicosLine(models.Model):
    _name = 'dgt_os.os.servicos.line'
    _description = 'Servicos Line'
    _order = 'os_id, sequence, id'

    name = fields.Char('Description', required=True)
    os_id = fields.Many2one(
        'dgt_os.os', 'Ordem de Serviço',
        index=True, ondelete='cascade')
    to_invoice = fields.Boolean('Faturar')
    product_id = fields.Many2one('product.product', u'Serviço', domain=[
                                 ('type', '=', 'service')], required=True)
    invoiced = fields.Boolean('Faturada', copy=False, readonly=True)
    automatic = fields.Boolean('Gerado automático', copy=False,  default=False)
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
        """On change of product it sets product quantity, tax account, name, uom of
        product, unit price and price subtotal."""
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom = self.product_id.uom_id.id
            self.product_uom = self.product_id.uom_id.id

    def can_unlink(self):
        if self.automatic:
            return False
        return True

    @api.multi
    def unlink(self):
        for item in self:
            if not item.can_unlink():
                raise UserError(
                    _('Serviço adicionado pelo sistema - Proibido excluir'))
        super(ServicosLine, self).unlink()
