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
            if self.login_required:
                self.redirect(users.create_login_url(self.request.url))
                return
        else:
            self.user_key = (User.query(User.user_id == self.user.user_id()).get(keys_only=True) or
                             User(user_id=self.user.user_id(), user_object=self.user).put())
        webapp2.RequestHandler.dispatch(self)

    def draw_page(self, template_name, **render_data):
        template = JINJA_ENVIRONMENT.get_template('templates/{}.html'.format(template_name))
        render_data['user_link'] = (users.create_logout_url('/') if self.user
                                    else users.create_login_url(self.request.url))
        if self.user:
            render_data['user_email'] = users.get_current_user().email()
        else:
            render_data['user_email'] = None
        render_data['is_admin'] = users.is_current_user_admin()
        self.response.write(template.render(render_data))



    def __init__(self, *args, **kwargs):
        self.login_required = False
        super(WebRequestHandler, self).__init__(*args, **kwargs)

