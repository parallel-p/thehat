__author__ = 'ivan'
import webapp2


class AllHandler(webapp2.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(AllHandler, self).__init__(*args, **kwargs)
