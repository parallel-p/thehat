__author__ = 'nikolay'
import webapp2


class PreGameNewHandler(webapp2.RequestHandler):
    def post(self):
        self.response.write('I\'ll create new pregame!')


class PreGameHandler(webapp2.RequestHandler):
    def get(self, game_id):
        self.response.write('I\'ll give pregame ' + game_id + '!')


class PreGameUpdateHandler(webapp2.RequestHandler):
    def post(self, game_id):
        self.response.write('I\'ll update pregame ' + game_id + '!')


class PreGameVersionHandler(webapp2.RequestHandler):
    def get(self, game_id):
        self.response.write('I\'ll give version of pregame ' + game_id + '!')


class PreGameSinceHandler(webapp2.RequestHandler):
    def get(self, game_id, version):
        self.response.write('I\'ll give diff of pregame ' + game_id + ' since ' + version + ' version!')


class PreGameStartHandler(webapp2.RequestHandler):
    def post(self, game_id):
        self.response.write('I\'ll start pregame ' + game_id + '!')


class PreGameAbortHandler(webapp2.RequestHandler):
    def post(self, game_id):
        self.response.write('I\'ll abort pregame ' + game_id + '!')


class PreGameJoinHandler(webapp2.RequestHandler):
    def post(self):
        self.response.write('I\'ll join some pregame!')
