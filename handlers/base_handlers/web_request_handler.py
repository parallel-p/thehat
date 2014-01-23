__author__ = 'ivan'

from google.appengine.api import users

from all_handler import AllHandler


class WebRequestHandler(AllHandler):
    def __init__(self, *args, **kwargs):
        super(WebRequestHandler, self).__init__(*args, **kwargs)
        if users.get_current_user() is None:
            self.redirect(users.create_login_url(self.request.uri))

