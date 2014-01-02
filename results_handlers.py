import webapp2


class ResultsHandler(webapp2.RequestHandler):
    def post(self, game_id):
        self.response.write('I\'ll give results to device from game with id ' + str(game_id))

    def get(self, game_id):
        self.response.write('I\'ll get results from game with id ' + str(game_id))
