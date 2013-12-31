import webapp2


class Change(webapp2.RequestHandler):
    def get(self):
        self.response.write('Pushing changes!')

class Update(webapp2.RequestHandler):
    def get(self):
        self.response.write('Getting changes!')