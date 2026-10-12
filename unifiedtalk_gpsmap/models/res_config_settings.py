from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gpsmap_activation_key = fields.Char(
        string='Activation key',
        config_parameter='unifiedtalk_gpsmap.activation_key',
    )
    gpsmap_gateway = fields.Char(
        string='Gateway',
        config_parameter='unifiedtalk_gpsmap.gateway',
        readonly=True,
    )
    gpsmap_registration_type = fields.Char(
        string='Registration type',
        config_parameter='unifiedtalk_gpsmap.registration_type',
        readonly=True,
    )
    gpsmap_application_id = fields.Char(
        string='Application',
        config_parameter='unifiedtalk_gpsmap.application_id',
        readonly=True,
    )
    gpsmap_company_id = fields.Char(
        string='Company',
        config_parameter='unifiedtalk_gpsmap.company_id',
        readonly=True,
    )

    def set_values(self):
        previous = (self.env['ir.config_parameter'].sudo().get_param('unifiedtalk_gpsmap.activation_key') or '').strip()
        new_key = (self.gpsmap_activation_key or '').strip()
        super().set_values()
        if new_key and new_key != previous:
            self.env['unifiedtalk.gpsmap.account'].activate(new_key, use_stored_gateway=bool(previous))
