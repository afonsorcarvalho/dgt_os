from odoo import models, fields, api

class EmailDgtOs(models.Model):
    """Classe que extende dgt_os.os e adiciona a funcionalidade de enviar e-mails"""
    _inherit = "dgt_os.os"

    email_to_send = fields.Char("E-mail alternativo",track_visibility='onchange')

    @api.multi
    def send_mail_template(self):
        # Find the e-mail template
        template = self.env.ref('dgt_os.dgt_os_email_template')
        # You can also find the e-mail template like this:
        # template = self.env['ir.model.data'].get_object('mail_template_demo', 'example_email_template')
 
        # Send out the e-mail template to the user

        #TODO verificar se o cliente possui um e-mail cadastrado ou se foi fornecido um e-mail alternativo
        #self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        self.message_post_with_view('dgt_os.dgt_os_email_template')

        
        
        