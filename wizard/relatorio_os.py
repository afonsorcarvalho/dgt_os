from odoo import fields, models, api, _
from io import BytesIO
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import xlwt
import base64
from datetime import datetime


class OSReportWizard(models.TransientModel):
    _name = "dgt_os.os.report.wizard"
    _description = "Wizard to generate a custom report for the model dgt_os.os"
    filter_model = fields.Reference(selection=[('res.partner', 'Cliente'), ('dgt_os.equipment', 'Equipamento'), ('hr.employee', 'Técnico')])
    date_from = fields.Date()
    date_to = fields.Date()
    report = fields.Binary('Relatório', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    name =  fields.Char('File Name', size=32)

    def check_report(self):
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Dgt Teste')
        fp = BytesIO()
        row = 0
        col = 0
        ws1.write(row, col, "OS")
        ws1.write(row, col + 1, "Data de execução")
        ws1.write(row, col + 2, "Cliente")
        ws1.write(row, col + 3, "Equipamento")
        ws1.write(row, col + 4, "Técnico")
        ws1.write(row, col + 5, "Tempo de execução")
        oses = self.buscar_oses(self.filter_model)
        row += 1
        for os in oses:
            ws1.write(row, col, os.name)
            ws1.write(row, col + 1, os.date_execution)
            ws1.write(row, col + 2, os.cliente_id.name)
            ws1.write(row, col + 3, os.equipment_id.name)
            ws1.write(row, col + 4, os.tecnicos_id.name)
            ws1.write(row, col + 5, os.time_execution)
      
            row +=1
           
        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get', 'report': out, 'name':'relatorio_oses.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dgt_os.os.report.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def buscar_oses(self, filtro):
        if type(filtro) == type(self.env['res.partner']):
            oses = self.env['dgt_os.os'].search([('cliente_id.name','=',self.filter_model.name), ('relatorios.data_atendimento', '>=', self.date_from), ('relatorios.data_atendimento', '<=', self.date_to)])
            return oses

        elif type(filtro) == type(self.env['dgt_os.equipment']):
            oses = self.env['dgt_os.os'].search([('equipment_id.name','=',self.filter_model.name), ('relatorios.data_atendimento', '>=', self.date_from), ('relatorios.data_atendimento', '<=', self.date_to)])
            return oses

        elif type(filtro) == type(self.env['hr.employee']):
            oses = self.env['dgt_os.os'].search([('tecnicos_id.name','=',self.filter_model.name), ('relatorios.data_atendimento', '>=', self.date_from), ('relatorios.data_atendimento', '<=', self.date_to)])
            return oses
        

