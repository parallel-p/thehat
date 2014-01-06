import webapp2
from objects.dictionaries_packages import PackagesStream, PackageDictionary
from environment import *
from google.appengine.api import users


def get_streams():
    streams_list = PackagesStream.query()
    streams = 'id name<br/>'
    for stream in streams_list:
        streams += "<a href='/streams/" + stream.id + "/packages/add'>" + stream.id + ' ' + stream.name + '</a><br/>'

    return streams


def get_packages(stream_id):
    packages_stream = PackagesStream.query(PackagesStream.id == stream_id).get()
    packages_list = []
    for package_id in packages_stream.packages_id_list:
        packages_list.append(PackageDictionary.query(PackageDictionary.id == package_id).get())

    packages = 'id name<br/>'
    for package in packages_list:
        packages += "<a href='/streams/packages/" + package.id + "/words'>" + \
                    package.id + ' ' + package.name + "</a><br/>"

    return packages


class AddStreamHandler(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user() and users.is_current_user_admin():
            template = JINJA_ENVIRONMENT.get_template('templates/streamsscreen.html')
            self.response.write(template.render({'streams': get_streams()}))
        else:
            self.redirect(users.create_login_url(self.request.uri))

    def post(self):
        if users.get_current_user() and users.is_current_user_admin():
            PackagesStream(id=self.request.get('stream_id'), name=self.request.get('stream_name'),
                           packages_id_list=[]).put()

            self.redirect('/streams')


class AddPackageHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        if users.get_current_user() and users.is_current_user_admin():
            template = JINJA_ENVIRONMENT.get_template('templates/packagesscreen.html')
            stream_id = kwargs.get('stream_id')
            self.response.write(template.render({'packages': get_packages(stream_id), 'stream_id': stream_id}))
        else:
            self.redirect(users.create_login_url(self.request.uri))

    def post(self, **kwargs):
        if users.get_current_user() and users.is_current_user_admin():
            PackageDictionary(id=self.request.get('package_id'), name=self.request.get('package_name'),
                              release_time=int(self.request.get('release_time')), words=[]).put()

            stream = PackagesStream.query(PackagesStream.id == kwargs.get('stream_id')).get()
            stream.packages_id_list.append(self.request.get('package_id'))
            stream.put()
            self.redirect('/streams/' + kwargs.get('stream_id') + '/packages/add')


class ChangeWordsHandler(webapp2.RequestHandler):
    def get(self, **kwargs):
        if users.get_current_user() and users.is_current_user_admin():
            template = JINJA_ENVIRONMENT.get_template('templates/packagewordsscreen.html')
            packages = PackageDictionary.query(PackageDictionary.id == kwargs.get('package_id')).fetch(1)
            if len(packages) == 0:
                self.error(404)
            else:
                list_words = packages[0].words
                words = ''
                for word in list_words:
                    words += '\n' + word
                self.response.write(
                    template.render({'package_id': kwargs.get('package_id'), 'words': words}))
        else:
            self.redirect(users.create_login_url(self.request.uri))

    def post(self, **kwargs):
        if users.get_current_user() and users.is_current_user_admin():
            words = self.request.get('text')
            list_word = []
            for word in words.strip().split('\n'):
                list_word.append(word.strip())

            package = PackageDictionary.query(PackageDictionary.id == kwargs.get('package_id')).get()
            package.words = list_word
            package.put()
            template = JINJA_ENVIRONMENT.get_template('templates/packagewordsscreen.html')
            self.response.write(template.render({'package_id': kwargs.get('package_id'), 'words': words}))