from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GpsMapUsername(models.Model):
    _name = 'unifiedtalk.gpsmap.username'
    _description = 'GPS Map username'
    _order = 'name'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='Odoo user', ondelete='set null')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Each SSO username can appear only once.'),
        ('user_unique', 'unique(user_id)', 'An Odoo user can have only one GPS Map username.'),
    ]

    def write(self, vals):
        previous = {row.id: row.user_id for row in self}
        result = super().write(vals)
        if 'user_id' in vals:
            self._sync_group(previous)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        rows = super().create(vals_list)
        rows._sync_group({})
        return rows

    def _sync_group(self, previous):
        group = self.env.ref('unifiedtalk_gpsmap.group_gps_map', raise_if_not_found=False)
        if not group:
            return
        field = self.env['unifiedtalk.gpsmap.account'].group_field()
        for row in self:
            old_user = previous.get(row.id)
            if old_user and old_user != row.user_id:
                old_user.with_context(gpsmap_skip_sync=True).write({field: [(3, group.id)]})
            if row.user_id:
                row.user_id.with_context(gpsmap_skip_sync=True).write({field: [(4, group.id)]})

    @api.constrains('user_id')
    def _check_registration_type(self):
        registration = self.env['unifiedtalk.gpsmap.account'].registration_type()
        if registration != 'limited' and any(row.user_id for row in self):
            raise UserError(_('Usernames can be assigned only when the activation key is limited.'))
