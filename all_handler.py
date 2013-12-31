__author__ = 'ivan'
import webapp2


class AllHandler(webapp2.RequestHandler):
    def __init__(self, *args, **kwargs):
        self.device_id = None
        super(AllHandler, self).__init__(*args, **kwargs)

    def set_device_id(self, **kwargs):
        self.device_id = kwargs.get('device_id', None)
