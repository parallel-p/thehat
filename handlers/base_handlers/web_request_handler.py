__author__ = 'ivan'

from google.appengine.api import users

from generic_handler import GenericHandler
import webapp2


class WebRequestHandler(GenericHandler):
    def dispatch(self):
        if users.get_current_user() is None:
            self.redirect(users.create_login_url())
        else:
            webapp2.RequestHandler.dispatch(self)

    def __init__(self, *args, **kwargs):
        super(WebRequestHandler, self).__init__(*args, **kwargs)

