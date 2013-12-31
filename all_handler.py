__author__ = 'ivan'
import webapp2

class AllHandler(webapp2.RequestHandler):

    def __init__(self, **kwargs):
        self.set_device_id = None
        super(AllHandler, self).__init__(*kwargs)

    def set_device_id(self, **kwargs):
        self.set_device_id = kwargs.get('device_id', None)
