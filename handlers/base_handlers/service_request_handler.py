__author__ = 'ivan'

from generic_handler import GenericHandler
from google.appengine.api import users


class ServiceRequestHandler(GenericHandler):
    def __init__(self, *args, **kwargs):
        super(ServiceRequestHandler, self).__init__(*args, **kwargs)

    def dispatch(self):
        super(ServiceRequestHandler, self).dispatch()

