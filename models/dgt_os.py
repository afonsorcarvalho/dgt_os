import time
from datetime import date, datetime,timedelta
from odoo import models, fields, api, _,SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class DgtOs(models.Model):
    _name = 'dgt_os.os'
    _description = 'Ordem de Serviço'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin','utm.mixin']
    _order = 'name'
    
    STATE_SELECTION = [
        ('draft', 'Criada'),
        ('under_budget', 'Em Orçamento'),
        ('pause_budget','Orçamento Pausado'),
        ('wait_authorization', 'Esperando aprovação'),
        ('execution_ready', 'Pronta para Execução'),
        ('under_repair', 'Em execução'),
        ('pause_repair','Execução Pausada'),
        ('done', 'Concluída'),
        ('cancel', 'Cancelada'),
    ]
 
    #TODO Transformar o tipo de manutenção em uma classe 
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
        
    sequence = fields.Integer(string='Sequence', default=10)
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
    maintenance_duration = fields.Float("Tempo Estimado", default='1.0',readonly=False)
    is_warranty = fields.Boolean(string="É garantia",  default=False)
    warranty_type = fields.Selection(string='Tipo de Garantia',selection=GARANTIA_SELECTION)
    date_scheduled = fields.Datetime('Scheduled Date', required=True, default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
    date_execution = fields.Datetime('Execution Date', required=True, default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
    date_start = fields.Datetime('Início da Execução', default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
    data_start_quotation = fields.Datetime('Início do orçamento', track_visibility='onchange', help='Data e hora do início do orçamento')
    data_stop_quotation = fields.Datetime('Fim do orçamento',track_visibility='onchange', help="Data de fim do orçamento")
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
    equipment_location = fields.Many2one( string = 'Setor de Uso',related='equipment_id.location_id', store=True)
    description = fields.Text(required=True, help="Descrição do serviço realizado ou a ser relalizado")
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement group', copy=False)
    #qr = fields.Text('Qr code',compute='_gera_qr',readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Conta analítica", )
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Posição Fiscal',  required=False,help='Posição fiscal para faturamento')
    check_list = fields.One2many('dgt_os.os.verify.list', 'dgt_os',track_visibility='onchange')
    check_list_created = fields.Boolean('Check List Created', track_visibility='onchange', default=False)
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
     # assinatura digital
    name_digital_signature_client = fields.Char(
        string=u'Nome do Cliente Assinatura',
    )
    signature_client_date = fields.Datetime(string="Data Assinatura do Cliente", default=time.strftime('%Y-%m-%d %H:%M:%S'),track_visibility='onchange')
    sign_client  = fields.Boolean(
        string='Assinado pelo cliente'
    )
    
    doc_digital_signature_client = fields.Char(
        string=u'Documento do Cliente Assinatura',
    )

    digital_signature_client = fields.Binary(string='Assinatura Cliente')
    gerado_cotacao = fields.Boolean(
        string=u'Cotação gerada?',
    )

    def set_sign_client(self):
        self.sign_client = 1

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
                _logger.debug("Mudando a quantidade para %s",self.maintenance_duration)
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
        #self.message_post(body=body)
        location_ref = self.env['stock.location']
        if len(self.tecnicos_id) > 0:
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
    
    def verify_execution_rules(self):
        if self.filtered(lambda dgt_os: dgt_os.state == 'done'):
                raise UserError(_("O.S já concluída."))
        if self.filtered(lambda dgt_os: dgt_os.state == 'under_repair'):
            raise UserError(_('O.S. já em execução.'))
        return

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
    def action_repair_pause(self):
        if self.filtered(lambda dgt_os: dgt_os.state != 'under_repair'):
            raise UserError(_("Repair must be canceled in order to reset it to draft."))
        
        return self.write({'state': 'pause_repair'})
    
    def relatorio_service_start(self,type_report):
        tecnicos_id = self.tecnicos_id
        motivo_chamado = ''
        servicos_executados = ''
        
        if type_report == 'quotation':
            motivo_chamado = 'Realizar Orçamento'
            servicos_executados = 'Orçamento'
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
            'type_report' : type_report,
            'cliente_id': self.cliente_id.id,
            'equipment_id': self.equipment_id.id,
            'tecnicos_id': tecnicos_id,
            'motivo_chamado': motivo_chamado,
            'servico_executados': servicos_executados,
            
        })

    def repair_relatorio_service_start(self):
        date_now = datetime.now()
        type_report = 'repair'
        self.relatorio_service_start(type_report)

    def quotation_relatorio_service_start(self):
        date_now = datetime.now()
        type_report = 'quotation'
        self.relatorio_service_start(type_report)
        

    def quotation_relatorio_service_end(self):
        date_now = datetime.now()
        type_report = 'quotation'
        data_atendimento = 	date.today()
        hora_fim = float(date_now.hour) + float(date_now.minute)/60
        relatorio_servico = self.env['dgt_os.os.relatorio.servico'].search([('os_id', '=', self.id),('type_report','=',type_report),('state','=','draft')])[0]
        if relatorio_servico.id:
            relatorio_servico.write({
                'hora_fim' : hora_fim,
                'state': 'done',
                
            })
    
    def set_agente_commission(self):
        _logger.debug("pegando agente comissão")
       
        for tec in self.tecnicos_id:
            rec = self.env['res.partner'].search([('name', '=',tec.name )], offset=0, limit=None, order=None, count=False)
            if len(rec) <= 0:
                raise UserError(_("Não foi encontrado nenhum técnico para comissionar. "))
            if rec.id:
                _logger.debug("Achado tecnico nome: %s, partner name: %s",tec.name,rec.name )
                if rec.agent:
                    _logger.debug("Técnico é representante")
                    _logger.debug("Tipo de representante: %s",rec.agent_type)
                    _logger.debug("Comissão é %s",rec.commission.name)
                    _logger.debug("Tipo de comissãp é %s",rec.commission.commission_type)
                    _logger.debug("Porcentagem é %s",rec.commission.fix_qty)
                    _logger.debug("Pegando a cotaçaõ ")
                    _logger.debug("Cotação %s", self.sale_id)
                    
                    for item_sale in self.sale_id.order_line:
                        _logger.debug("item %s", item_sale.name)
                        _logger.debug("procurando comissão")
                        if len(item_sale.agents):
                            for item_agents in item_sale.agents:
                                _logger.debug("O representante do item é  %s", item_agents.agent.name)
                                _logger.debug("Nome da comissão  %s", item_agents.agent.commission.name)
                                _logger.debug("Valor da comissão  %s", item_agents.amount)
                        else:
                            _logger.debug("Nenhuma comissão colocada  ")
                            _logger.debug("Tipo de order line  %s", item_sale.display_type)
                            if item_sale.display_type == 'line_section' or item_sale.display_type == 'line_note':
                                _logger.debug("Esta linha não se coloca representante")
                            else:
                               
                                _logger.debug("Adicionando representante da comissão %s", rec.agent_type)
                                _logger.debug("Comission %s",rec.commission.id )
                               
                                res = item_sale.write({
                                    'agents': [(0,0,{
                                        'agent': rec.id,
                                        'commission': rec.commission.id
                                    }
                                    )]
                                }
                                    
                                )
                                _logger.debug("salvo comissão, resultado:")
                                _logger.debug(res)
                else:
                    _logger.debug("tecnico não é representante" )
            else:
                _logger.debug("Não foi achado tecnico nome: %s, partner name: %s",tec.name,rec.name )
                
    @api.multi
    def finish_report(self):
        _logger.debug("Procurando relatorios...")
        if self.relatorios:
            for rec in self.relatorios:
                rec.state = 'done'
        return True
    
    #utilizado na venda para atorizar Ordem de serviço        
    @api.multi
    def approve(self):
        _logger.debug("Mudando state da os %s",self.name)
        for item in self:
            if item.state != 'done':
                item.write({'state': 'execution_ready'})
        _logger.debug("os state=%s ", self.state)
        
    #TODO Colocar também o técnico que irá receber a comissão 
    # colocar tempo de execução no serviço do contrato, mas isso tem que ser feito ao realizar fim da execução ou qd 
    # aciona o botão de gerar o orçamento   
    def gera_orcamento(self):
        if self.filtered(lambda dgt_os: dgt_os.gerado_cotacao == True):
            raise UserError(_("Cotação para esse Ordem de serviço já foi gerada"))
        if not len(self.servicos):
            raise UserError(_("Para gerar cotação deve ter pelo menos um serviço adicionado"))
        if self.state == 'under_budget':
            _logger.debug("Ordem de serviço em orçamento")    
            _logger.debug("Procura serviço para atualizar tempo")
            
          
                        
        _logger.debug("posicão fiscal: %s",self.fiscal_position_id.name)
        _logger.debug("Conta Analítica: %s",self.analytic_account_id.name )
        _logger.debug("Gerando cotação para %s:",self.name)
        
        
        saleorder = self.env['sale.order'].create({
            "origin": self.name,
            "partner_id" : self.cliente_id.id,
            "os_id": self.id,
            "analytic_account_id":self.analytic_account_id.id,
            "fiscal_position_id":self.fiscal_position_id.id,
            
        })
        _logger.info("Sale_order gerada: %s", saleorder.name)
        _logger.debug(saleorder)

        if saleorder.id:
            _logger.debug("criar linhas da sale.order:")
            _logger.debug(saleorder.name)
            
            name_note = "Referente ao equipamento "
            if self.equipment_id.name: name_note = name_note + self.equipment_id.name
            #if self.equipment_id.category_id.name: name_note = name_note + self.equipment_id.category_id.name
            if self.equipment_serial_number: name_note = name_note + " NS " + str(self.equipment_serial_number)
            if self.equipment_model: name_note = name_note + " Modelo: " + str(self.equipment_model)
               
            # Adicionando as peças
            _logger.debug("Adicionando notas explicativas da cotação: %s", name_note)
            self.env['sale.order.line'].create({
                    'name' : name_note,
                    'display_type' : 'line_note',
                    'order_id': saleorder.id,
                    'product_id': False,
                    'product_uom': False,
                    
                })
            secao_str = "Peças da " + self.name +":"
            _logger.debug("Adicionando seção peça da cotação: %s", secao_str)
            self.env['sale.order.line'].create({
                    'name' : secao_str,
                    'display_type' : 'line_section',
                    'order_id': saleorder.id,
                    'product_id': False,
                    'product_uom': False,
                    
                })
            _logger.debug("Sessão criada!!!")
            _logger.debug("Adicionando linhas de pecas:")
            for peca in self.pecas:
                
                saleline = self.env['sale.order.line'].create({
                    
                    'order_id': saleorder.id,
                    'product_id': peca.product_id.id,
                    'product_uom_qty': peca.product_uom_qty,
                    'product_uom': peca.product_uom.id,
                    'invoice_lines': peca.invoice_line_id.id,
                })
                _logger.debug("Adicionado peça %s, qty %s", saleline.product_id.name, saleline.product_uom_qty)
                
            
            #adicionando serviços
            _logger.debug("Adicionando seção de serviços:")
            self.env['sale.order.line'].create({
                    'name' : "Serviços da " + self.name + ":",
                    'display_type' : 'line_section',
                    'order_id': saleorder.id,
                    'product_id': False,
                    'product_uom': False,
                    
                })
            _logger.debug("Sessão serviços criada!!!")
            #TODO Pegar do contrato o serviço product_id caso tenha configurado no contrato
            for servico in self.servicos:
                _logger.info("adicionando linhas:")
                saleline = self.env['sale.order.line'].create({
                    
                    'order_id': saleorder.id,
                    'product_id': servico.product_id.id,
                    'product_uom_qty': servico.product_uom_qty,
                    'product_uom': servico.product_uom.id,
                    'invoice_lines': servico.invoice_line_id.id,
                })
                _logger.debug("Adicionado serviço %s, qty %s", saleline.product_id.name, saleline.product_uom_qty)
              
            
            self.write({'sale_id': saleorder.id,'gerado_cotacao': True})   
            self.set_agente_commission()
        
        return True
    # apenas usado para teste de pegar o representante com suas comissões
    #TODO
    # apagar essa action após desenvolvimento
    def action_agente(self):
        self.set_agente_commission()
        
    @api.multi
    def action_quotation_start(self):
        self.message_post(body='Iniciada orçamento da ordem de serviço!')
        self.quotation_relatorio_service_start()
        _logger.debug("Iniciando Orçamento")
        res = self.write({'state': 'under_budget', 'date_start_quotation': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    @api.multi
    def action_quotation_pause(self):
        self.message_post(body='Pausado orçamento da ordem de serviço!')
        self.quotation_relatorio_service_end()
        res = self.write({'state': 'pause_budget'})
        return res
    
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
    def action_repair_executar(self):
        
        self.verify_execution_rules()
        if self.state == 'draft' or self.state == 'execution_ready':
            _logger.debug("Criando Check List")
            self.create_checklist()
        self.message_post(body='Iniciada execução da ordem de serviço!')
        res = self.write({'state': 'under_repair', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    @api.multi
    def action_pause_repair_executar(self):
        
        self.verify_execution_rules()
        self.create_checklist()
        self.message_post(body='Pausada execução da ordem de serviço!')
        res = self.write({'state': 'under_repair', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    @api.multi
    def action_repair_cancel(self):
        self.mapped('pecas').write({'state': 'cancel'})
        return self.write({'state': 'cancel'})
    
                    
    @api.multi
    def action_repair_end(self):
        """Writes repair order state to 'To be invoiced' if invoice method is After
        repair else state is set to 'Ready'.

        @return: True
        """
            
        if self.filtered(lambda dgt_os: dgt_os.state != 'under_repair'):
            raise UserError(_("A ordem de serviço de estar \"em execução\" para finalizar a execução."))

        if self.filtered(lambda dgt_os: dgt_os.state == 'done'):
            raise UserError(_('Ordem já finalizada'))

        if not self.relatorios:	
            raise UserError(_("Para finalizar O.S. deve-se incluir pelo menos um relatório de serviço."))
            return False
        
        if self.check_list_created:
            for check in self.check_list:	
                if not check.check:
                    raise UserError(_("Para finalizar O.S. todas as instruções do check-list devem estar concluídas"))
                    return False
                    
        
        vals = {
                'state': 'done',
                'date_execution': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        #self.action_repair_done()
        res = self.write(vals)
        if res:
            if self.sale_id.id:
                _logger.debug("Cotação já foi gerada: %s",self.sale_id.name)
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
       

    def create_checklist(self):
        """Cria a lista de verificacao caso a os seja preventiva."""
        if self.maintenance_type == 'preventive' or self.maintenance_type == 'loan' or self.maintenance_type == 'calibration' :
            _logger.debug("Criando Checklis")
            instructions = self.env['maintenance.equipment.category.vl'].search([('category_id.name', '=', self.equipment_id.category_id.name)])
            os_check_list = self.env['dgt_os.os.verify.list'].search([('category_id.name', '=', self.equipment_id.category_id.name)])
            

            for i in instructions:
                instructions =os_check_list.create({'dgt_os': self.id, 'instruction': str(i.name)})
                _logger.debug(instructions)
                
            self.check_list_created = True

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
            
class RelatoriosServico(models.Model):
    _name = 'dgt_os.os.relatorio.servico'	
    _inherit = ['mail.thread']
    _order = 'data_atendimento'

    date_now = fields.datetime.now()
    name = fields.Char(
        'Nº Relatório de Serviço',default=lambda self: self.env['ir.sequence'].next_by_code('dgt_os.os.relatorio'),
        copy=False, required=True)
    state = fields.Selection(string='Status', selection=[('draft', 'rascunho'), ('done', 'Concluído')], default='draft')
    type_report = fields.Selection(string='Tipo de Relatório', selection=[('quotation', 'Orçamento'), ('repair', 'Manutenção'),('calibrate', 'Calibração')], default="repair")
    
    os_id = fields.Many2one(
        'dgt_os.os', 'Ordem de serviço',
        index=True, ondelete='cascade')
    cliente_id = fields.Many2one('res.partner', string='Owner',
        compute='_compute_relatorio_default',
        track_visibility='onchange',store=True)
    observations = fields.Char(string='Observações')
    
    relatorio_num = fields.Char('Nº Relatório')
    data_atendimento = fields.Date('Data atendimento', required=True, default=fields.date.today() )
    hora_inicio = fields.Float('Hora de início', default = float(fields.datetime.now().hour) + float(fields.datetime.now().minute)/60, required=True)
    hora_termino = fields.Float('Hora de termino',default = float(fields.datetime.now().hour + 1) + float(fields.datetime.now().minute)/60, required=True)
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
    tem_defeitos = fields.Boolean(string='tem defeitos?', default = False)
    defeitos = fields.Text('Descreva tecnicamente o defeito apresentado')
    servico_executados = fields.Text('Descreva o serviço realizado')
    tem_pendencias = fields.Boolean('Tem pendencias?', default = False)
    pendencias = fields.Text('Descreva pendências')
    
    
    #atendimentos = fields.One2many(
    #	'dgt_os.os.relatorio.atendimento.line', 'relatorio_id', 'Atendimento',
    #	 readonly=False)
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
    @api.depends('os_id','os_id.cliente_id','os_id.equipment_id','os_id.tecnicos_id','os_id.description')
    def _compute_relatorio_default(self):
        self.cliente_id = self.os_id.cliente_id.id
        self.equipment_id = self.os_id.equipment_id.id
        self.tecnicos_id = self.os_id.tecnicos_id
        self.motivo_chamado = self.os_id.description
        if self.os_id.state == 'under_budget':
            self.servico_executados = 'Realizado Orçamento'
      
            
        

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
