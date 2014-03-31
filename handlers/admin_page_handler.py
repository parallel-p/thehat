__author__ = 'ivan'
from google.appengine.api import users
import webapp2

from environment import JINJA_ENVIRONMENT
from base_handlers.admin_request_handler import AdminRequestHandler


class AdminPage(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AdminPage, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        self.draw_page('admin')