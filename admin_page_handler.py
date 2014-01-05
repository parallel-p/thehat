__author__ = 'ivan'
from environment import JINJA_ENVIRONMENT
import webapp2
from google.appengine.api import users

class AdminPage(webapp2.RequestHandler):
    def get(self):
        if not users.is_current_user_admin():
            self.redirect(users.create_login_url(self.request.uri))
        template = JINJA_ENVIRONMENT.get_template('templates/admin.html')
        self.response.write(template.render())