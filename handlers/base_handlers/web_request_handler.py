__author__ = 'ivan'

from google.appengine.api import users

from generic_handler import GenericHandler
from objects.user_devices import User

import webapp2
from environment import JINJA_ENVIRONMENT


class WebRequestHandler(GenericHandler):
    user_key = None
    user = None

    def dispatch(self):
        self.user = users.get_current_user()
        if self.user is None:
            self.redirect(users.create_login_url(self.request.url))
        else:
            self.user_key = (User.query(User.user_id == self.user.user_id()).get(keys_only=True) or
                             User(user_id=self.user.user_id(), user_object=self.user).put())
            webapp2.RequestHandler.dispatch(self)

    def draw_page(self, template_name, **render_data):
        template = JINJA_ENVIRONMENT.get_template('templates/{}.html'.format(template_name))
        render_data['logout_link'] = users.create_logout_url('/')
        render_data['user_email'] = users.get_current_user().email()
        self.response.write(template.render(render_data))



    def __init__(self, *args, **kwargs):
        super(WebRequestHandler, self).__init__(*args, **kwargs)

