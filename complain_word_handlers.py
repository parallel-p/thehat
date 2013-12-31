__author__ = 'ivan'

import webapp2

class ComplainWordHandler(webapp2.RequestHandler):

    def post(self, **kwargs):
        self.response.write('post, ok')

    def get(self, **kwargs):
        self.response.write('get, ok')
