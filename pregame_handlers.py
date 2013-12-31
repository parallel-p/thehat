__author__ = 'nikolay'
import webapp2

class PreGameAllHandler(webapp2.RequestHandler):
    def set_device_id(self, **kwargs):
        self.device_id = kwargs.get('device_id', None)


class PreGameNewHandler(PreGameAllHandler):
    def post(self, **kwargs):
        super(PreGameNewHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll create new pregame! device_id = %s' % self.device_id)


class PreGameHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        self.response.write('I\'ll give pregame!')


class PreGameUpdateHandler(webapp2.RequestHandler):
    def post(self, **kwargs):
        self.response.write('I\'ll update pregame!')


class PreGameVersionHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        self.response.write('I\'ll give version of pregame!')


class PreGameSinceHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        self.response.write('I\'ll give diff of pregame since  version!')


class PreGameStartHandler(webapp2.RequestHandler):
    def post(self, **kwargs):
        self.response.write('I\'ll start pregame !')


class PreGameAbortHandler(webapp2.RequestHandler):
    def post(self, **kwargs):
        self.response.write('I\'ll abort pregame !')


class PreGameJoinHandler(webapp2.RequestHandler):
    def post(self, **kwargs):
        self.response.write('I\'ll join some pregame!')
