__author__ = 'ivan'
from google.appengine.api import users
import webapp2

from environment import JINJA_ENVIRONMENT
from base_handlers.admin_request_handler import AdminRequestHandler


class AdminPage(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AdminPage, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/admin.html')
        self.response.write(template.render(
            {"logout_link": users.create_logout_url('/')}))