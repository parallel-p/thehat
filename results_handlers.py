import webapp2

class PostResultsHandler(webapp2.RequestHandler):
    def post(self, id):
        self.response.write('I\'ll give results to device from game with id №' + id)

class GetResultsHandler(webapp2.RequestHandler):
    def get(self, id):
        self.response.write('I\'ll get results from game with id №' + id)
