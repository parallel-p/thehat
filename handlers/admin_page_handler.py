__author__ = 'ivan'
from google.appengine.api import users

from environment import JINJA_ENVIRONMENT
from base_handlers.admin_request_handler import AdminRequestHandler


class AdminPage(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AdminPage, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/admin.html')
        if users.get_current_user():
            self.response.write(template.render(
                {"logout_link": users.create_logout_url('/')}))
        else:
            self.response.write(template.render({}))