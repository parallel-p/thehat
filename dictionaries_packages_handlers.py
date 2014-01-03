import webapp2
import json


class GetStreamsListHandler(webapp2.RedirectHandler):
    def get(self, **kwargs):
        streams_list = [{"id": "1", "name": "stream1"}, {"id": "2", "name": "stream2"}]

        json_obj = {"streams": streams_list}

        self.response.write(json.dumps(json_obj))
        #self.response.write('I\'ll give list of streams!')


class ChangeStreamStateHandler(webapp2.RedirectHandler):
    def post(self, **kwargs):
        self.response.write('I\'ll change state of stream ' +
                            kwargs.get('stream_id', "") + ' to ' +
                            kwargs.get('on', "") + '!')


class GetPackagesListHandler(webapp2.RedirectHandler):
    def get(self, **kwargs):
        packages_list = [{"id": "1", "name": "package1", "release_time": 1},
                         {"id": "2", "name": "package2", "release_time": 2}]

        json_obj = {"packages": packages_list}

        self.response.write(json.dumps(json_obj))
        #self.response.write('I\'ll give list of packages from stream '
        #                    + kwargs.get('stream_id', None) + '!')


class GetPackageHandler(webapp2.RedirectHandler):
    def get(self, **kwargs):
        package1 = {"id": "1", "name": "package1", "release_time": 1, "words": ["tea", "coffee"]}

        self.response.write(json.dumps(package1));
        #self.response.write('I\'ll give package ' +
        #                    kwargs.get('package_id', None) + '!')
