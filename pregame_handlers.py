__author__ = 'nikolay'
import webapp2
from all_handler import AllHandler


class PreGameCreateHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameCreateHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll create new pregame! device_id = %s' % self.device_id)


class PreGameHandler(AllHandler):
    def get(self, **kwargs):
        super(PreGameHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll give pregame!')


class PreGameUpdateHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameUpdateHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll update pregame!')


class PreGameVersionHandler(AllHandler):
    def get(self, **kwargs):
        super(PreGameVersionHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll give version of pregame!')


class PreGameSinceHandler(AllHandler):
    def get(self, **kwargs):
        super(PreGameSinceHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll give diff of pregame since some version!')


class PreGameStartHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameStartHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll start pregame !')


class PreGameAbortHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameAbortHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll abort pregame !')


class PreGameJoinHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameJoinHandler, self).set_device_id(**kwargs)
        self.response.write('I\'ll join some pregame!')
