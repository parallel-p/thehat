__author__ = 'ivan'

from google.appengine.api import users

from web_request_handler import WebRequestHandler
import webapp2


class AdminRequestHandler(WebRequestHandler):

    def dispatch(self):
        if users.get_current_user() is None:
            self.redirect(users.create_login_url())
        elif not users.is_current_user_admin():
            self.redirect('/')
        else:
            webapp2.RequestHandler.dispatch(self)

    def __init__(self, *args, **kwargs):
        super(AdminRequestHandler, self).__init__(*args, **kwargs)

