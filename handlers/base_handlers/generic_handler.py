__author__ = 'ivan'
import webapp2


class GenericHandler(webapp2.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(GenericHandler, self).__init__(*args, **kwargs)
