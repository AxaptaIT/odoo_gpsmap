import html
from urllib.parse import urlencode

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request


class GpsMapController(http.Controller):

    @http.route('/gpsmap/open', type='http', auth='user', website=False)
    def open_map(self):
        account = request.env['unifiedtalk.gpsmap.account']
        user = request.env.user
        if not account.activated():
            return self._page('Setup is not finished. An administrator must enter the activation key.')
        registration = account.registration_type()
        if registration not in ('enterprise', 'limited'):
            return self._page('This activation key is not valid.')
        if registration == 'enterprise' and not user.has_group('unifiedtalk_gpsmap.group_gps_map'):
            return self._page('An administrator must add you to the GPS Map group.')
        if registration == 'limited':
            assigned = request.env['unifiedtalk.gpsmap.username'].sudo().search([('user_id', '=', user.id)], limit=1)
            if not assigned:
                return self._page('An administrator must assign a GPS Map username to you.')
        try:
            handoff = account.handoff(user)
        except UserError as error:
            return self._page(str(error))
        back_url = (handoff.get('backUrl') or '').rstrip('/')
        token = handoff.get('accessToken') or ''
        journey = handoff.get('journeyId') or ''
        if not back_url or not token or not journey:
            return self._page('The GPS service did not return a sign-in link.')
        lang = 'ar' if (user.lang or '').lower().startswith('ar') else 'en'
        query = urlencode({'lang': lang, 'token': token, 'sessionId': journey})
        return request.redirect(f'{back_url}/apploading?{query}')

    def _page(self, message):
        body = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>GPS Map</title></head>'
            '<body style="font-family:Segoe UI,Tahoma,sans-serif;margin:2rem;color:#4a463f;">'
            f'<p>{html.escape(message)}</p></body></html>'
        )
        return request.make_response(body, headers=[('Content-Type', 'text/html; charset=utf-8')])
