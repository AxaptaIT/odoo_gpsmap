import json
import urllib.error
import urllib.request

from odoo import _, models
from odoo.exceptions import UserError

ACTIVATION_URL = 'https://gateway.unifiedtalk.com/api/sso/AppAuth/ActivateOdoo'


class GpsMapAccount(models.AbstractModel):
    _name = 'unifiedtalk.gpsmap.account'
    _description = 'GPS Map account'

    def _params(self):
        return self.env['ir.config_parameter'].sudo()

    def _get(self, key):
        return (self._params().get_param(key) or '').strip()

    def activated(self):
        return bool(self._get('unifiedtalk_gpsmap.activation_key') and self._get('unifiedtalk_gpsmap.gateway'))

    def odoo_username(self, user):
        return (user.login or '').strip()

    def person_name(self, user):
        parts = (user.name or '').strip().split(' ', 1)
        first = parts[0] if parts and parts[0] else ''
        last = parts[1] if len(parts) > 1 else ''
        return first, last

    def group_field(self):
        users = self.env['res.users']
        if 'group_ids' in users._fields:
            return 'group_ids'
        return 'groups_id'

    def activate(self, activation_key, use_stored_gateway=False):
        key = (activation_key or '').strip()
        if not key:
            raise UserError(_('Enter the activation key.'))
        if use_stored_gateway and self._get('unifiedtalk_gpsmap.gateway'):
            url = self._get('unifiedtalk_gpsmap.gateway').rstrip('/') + '/api/sso/AppAuth/ActivateOdoo'
        else:
            url = ACTIVATION_URL
        user = self.env.user
        first, last = self.person_name(user)
        payload = self._post(url, {
            'activationKey': key,
            'userName': self.odoo_username(user),
            'firstName': first,
            'lastName': last,
        })
        registration = self.normalize_type(payload.get('registrationType'))
        gateway = (payload.get('gateway') or '').strip().rstrip('/')
        application_id = (payload.get('applicationId') or '').strip()
        company_id = (payload.get('companyId') or '').strip()
        if registration not in ('enterprise', 'limited') or not gateway or not application_id or not company_id:
            raise UserError(_('The activation key did not return a complete setup.'))
        params = self._params()
        params.set_param('unifiedtalk_gpsmap.activation_key', key)
        params.set_param('unifiedtalk_gpsmap.gateway', gateway)
        params.set_param('unifiedtalk_gpsmap.application_id', application_id)
        params.set_param('unifiedtalk_gpsmap.company_id', company_id)
        params.set_param('unifiedtalk_gpsmap.registration_type', registration)
        self._store_usernames(payload.get('userNames') or [])
        return payload

    def ensure_user(self, user, remove=False):
        username = self.odoo_username(user)
        if not username:
            raise UserError(_('This Odoo user needs a username before they can be added to GPS Map.'))
        first, last = self.person_name(user)
        self._post(self._gateway_url('EnsureOdooUser'), {
            'activationKey': self._get('unifiedtalk_gpsmap.activation_key'),
            'userName': username,
            'firstName': first,
            'lastName': last,
            'remove': bool(remove),
        })

    def normalize_type(self, value):
        registration = (value or '').strip().lower()
        return {'open': 'enterprise', 'permitted': 'limited'}.get(registration, registration)

    def registration_type(self):
        return self.normalize_type(self._get('unifiedtalk_gpsmap.registration_type'))

    def handoff(self, user):
        registration = self.registration_type()
        body = {'activationKey': self._get('unifiedtalk_gpsmap.activation_key')}
        if registration == 'limited':
            assigned = self.env['unifiedtalk.gpsmap.username'].sudo().search([('user_id', '=', user.id)], limit=1)
            if not assigned:
                raise UserError(_('An administrator must assign a GPS Map username to you.'))
            body['userName'] = assigned.name
        elif registration == 'enterprise':
            username = self.odoo_username(user)
            if not username:
                raise UserError(_('This Odoo user needs a username before the map can open.'))
            body['userName'] = username
        else:
            raise UserError(_('This activation key is not valid.'))
        return self._post(self._gateway_url('OdooHandoff'), body)

    def deactivate(self):
        key = self._get('unifiedtalk_gpsmap.activation_key')
        gateway = self._get('unifiedtalk_gpsmap.gateway')
        if not key or not gateway:
            return
        self._post(self._gateway_url('DeactivateOdoo'), {'activationKey': key})

    def action_open(self):
        if not self.activated():
            if self.env.user.has_group('base.group_system'):
                action = self.env.ref('unifiedtalk_gpsmap.action_activation_wizard').sudo().read()[0]
                return action
            return self._notice(_('Setup is not finished. An administrator must enter the activation key.'))
        registration = self.registration_type()
        user = self.env.user
        if registration not in ('enterprise', 'limited'):
            return self._notice(_('This activation key is not valid.'))
        if registration == 'enterprise' and not user.has_group('unifiedtalk_gpsmap.group_gps_map'):
            return self._notice(_('An administrator must add you to the GPS Map group.'))
        if registration == 'limited':
            assigned = self.env['unifiedtalk.gpsmap.username'].sudo().search([('user_id', '=', user.id)], limit=1)
            if not assigned:
                return self._notice(_('An administrator must assign a GPS Map username to you.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/gpsmap/open',
            'target': 'self',
        }

    def _store_usernames(self, names):
        wanted = []
        for name in names:
            cleaned = (name or '').strip()
            if cleaned and cleaned not in wanted:
                wanted.append(cleaned)
        username = self.env['unifiedtalk.gpsmap.username'].sudo()
        existing = {row.name: row for row in username.search([])}
        for name in wanted:
            if name not in existing:
                username.create({'name': name})
        for name, row in existing.items():
            if name not in wanted:
                row.unlink()

    def _gateway_url(self, action):
        gateway = self._get('unifiedtalk_gpsmap.gateway')
        if not gateway:
            raise UserError(_('GPS Map is not activated.'))
        return gateway.rstrip('/') + '/api/sso/AppAuth/' + action

    def _post(self, url, payload):
        data = json.dumps(payload).encode()
        request = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as error:
            raw = error.read().decode(errors='replace')
            message = self._error_message(raw) or _('The GPS service rejected the request.')
            raise UserError(message) from error
        except urllib.error.URLError as error:
            raise UserError(_('The GPS service could not be reached.')) from error
        if not raw:
            return {}
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as error:
            raise UserError(_('The GPS service returned an unexpected response.')) from error
        if not isinstance(body, dict):
            raise UserError(_('The GPS service returned an unexpected response.'))
        return body

    def _error_message(self, raw):
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return ''
        if isinstance(body, dict):
            return body.get('message') or body.get('Message') or ''
        return ''

    def _notice(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('GPS Map'),
                'message': message,
                'type': 'warning',
                'sticky': False,
            },
        }
