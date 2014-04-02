__author__ = 'ivan'

from google.appengine.api import users

from web_request_handler import WebRequestHandler
import webapp2


class AdminRequestHandler(WebRequestHandler):

    def dispatch(self):
        if users.get_current_user() is None:
            self.redirect(users.create_login_url())
        if not users.is_current_user_admin():
            self.redirect('/')
        else:
            WebRequestHandler.dispatch(self)

    def __init__(self, *args, **kwargs):
        super(AdminRequestHandler, self).__init__(*args, **kwargs)
        self.login_required = True


