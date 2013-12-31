import webapp2


class GetStreamsListHandler(webapp2.RedirectHandler):
    def get(self):
        self.response.write('I\'ll give list of streams!')


class ChangeStreamStateHandler(webapp2.RedirectHandler):
    def post(self, stream_id, on):
        self.response.write('I\'ll change state of stream ' + stream_id + ' to ' + on + '!')


class GetPackagesListHandler(webapp2.RedirectHandler):
    def get(self, stream_id):
        self.response.write('I\'ll give list of packages from stream ' + stream_id + '!')


class GetPackageHandler(webapp2.RedirectHandler):
    def get(self, package_id):
        self.response.write('I\'ll give package ' + package_id + '!')
