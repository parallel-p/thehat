__author__ = 'ivan'

from generic_handler import GenericHandler
from google.appengine.api import users


class ServiceRequestHandler(GenericHandler):
    def __init__(self, *args, **kwargs):
        super(ServiceRequestHandler, self).__init__(*args, **kwargs)

    def dispatch(self):
        if not users.is_current_user_admin():
            self.abort(403)
        super(ServiceRequestHandler, self).dispatch()

