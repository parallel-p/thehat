__author__ = 'ivan'

from google.appengine.api import users

from generic_handler import GenericHandler
from objects.user_devices import User
import webapp2


class WebRequestHandler(GenericHandler):
    user_key = None
    user = None

    def dispatch(self):
        self.user = users.get_current_user()
        if self.user is None:
            self.redirect(users.create_login_url())
        else:
            self.user_key = (User.query(User.user_id == self.user.user_id()).get(keys_only=True) or
                             User(user_id=self.user.user_id(), user_object=self.user)).put()
            webapp2.RequestHandler.dispatch(self)

    def __init__(self, *args, **kwargs):
        super(WebRequestHandler, self).__init__(*args, **kwargs)

