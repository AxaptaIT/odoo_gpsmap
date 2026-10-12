from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        account = self.env['unifiedtalk.gpsmap.account']
        field = account.group_field()
        group = self.env.ref('unifiedtalk_gpsmap.group_gps_map', raise_if_not_found=False)
        watch = (
            group
            and field in vals
            and not self.env.context.get('gpsmap_skip_sync')
            and account._get('unifiedtalk_gpsmap.registration_type') == 'open'
        )
        before = {}
        if watch:
            before = {user.id: group in user[field] for user in self}
        result = super().write(vals)
        if watch:
            for user in self:
                was_member = before.get(user.id)
                is_member = group in user[field]
                if not was_member and is_member:
                    account.ensure_user(user)
                elif was_member and not is_member:
                    account.ensure_user(user, remove=True)
        return result
