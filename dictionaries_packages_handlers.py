import webapp2


class GetStreamsListHandler(webapp2.RedirectHandler):
    def get(self, **kwargs):
        self.response.write('I\'ll give list of streams!')


class ChangeStreamStateHandler(webapp2.RedirectHandler):
    def post(self, **kwargs):
        self.response.write('I\'ll change state of stream ' +
                            kwargs.get('stream_id', None) + ' to ' +
                            kwargs.get('on', None) + '!')


class GetPackagesListHandler(webapp2.RedirectHandler):
    def get(self, **kwargs):
        self.response.write('I\'ll give list of packages from stream '
                            + kwargs.get('stream_id', None) + '!')


class GetPackageHandler(webapp2.RedirectHandler):
    def get(self, **kwargs):
        self.response.write('I\'ll give package ' +
                            kwargs.get('package_id', None) + '!')
