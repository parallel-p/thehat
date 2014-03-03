import constants

__author__ = 'denspb'

from google.appengine.api import users

from handlers.base_handlers.api_request_handlers import AuthorizedAPIRequestHandler


class LinkDevice(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(LinkDevice, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        user = users.get_current_user()
        if user is None:
            self.abort(403)
        self.response.write(self.device_id)

