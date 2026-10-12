from odoo import fields, models


class GpsMapActivation(models.TransientModel):
    _name = 'unifiedtalk.gpsmap.activation'
    _description = 'GPS Map activation'

    activation_key = fields.Char(string='Activation key', required=True)

    def action_activate(self):
        self.env['unifiedtalk.gpsmap.account'].activate(self.activation_key, use_stored_gateway=False)
        return {'type': 'ir.actions.act_window_close'}
