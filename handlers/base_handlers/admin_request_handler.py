__author__ = 'ivan'

from google.appengine.api import users

from web_request_handler import WebRequestHandler


class AdminRequestHandler(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AdminRequestHandler, self).__init__(*args, **kwargs)
        if not users.is_current_user_admin():
            self.error(401)

