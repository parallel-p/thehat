import json
import webapp2
from google.appengine.api import users
from all_handler import AllHandler
from objects.user_devices import get_user_by_device
from objects.user_streams import UserStreams
from objects.dictionaries_packages import PackagesStream, PackageDictionary
from google.appengine.ext import ndb
from environment import *


class AddStreamHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        PackagesStream(id=kwargs.get('stream_id'), name=kwargs.get('stream_name'), packages_id_list=[]).put()


class AddPackageHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        PackageDictionary(id=kwargs.get('package_id'), name=kwargs.get('package_name'),
                          release_time=int(kwargs.get('release_time')), words=[]).put()

        stream = PackagesStream.query(PackagesStream.id == kwargs.get('stream_id')).get()
        stream.packages_id_list.append(kwargs.get('package_id'))
        stream.put()
        self.response.write('Package ' + kwargs.get('package_id') + ' added to stream ' + kwargs.get('stream_id'))


class ChangeWordsHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/packagewordsscreen.html')
        packages = PackageDictionary.query(PackageDictionary.id == kwargs.get('package_id')).fetch(1)
        if len(packages) == 0:
            self.error(404)
        else:
            list_words = packages[0].words
            words = ''
            for word in list_words:
                words += '\n' + word
            self.response.write(template.render({'package_id': kwargs.get('package_id'), 'words': words, 'error': 'error'}))

    def post(self, **kwargs):
        words = self.request.get('text').strip().split('\n')
        list_word = []
        for word in words:
            list_word.append(word.strip())

        package = PackageDictionary.query(PackageDictionary.id == kwargs.get('package_id')).get()
        package.words = list_word
        package.put()
        self.response.write('Words added')