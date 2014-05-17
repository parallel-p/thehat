from google.appengine.api import users
from handlers import AdminRequestHandler

from objects.dictionaries_packages import PackagesStream, PackageDictionary
from environment import *


def get_streams():
    streams_list = PackagesStream.query()
    streams = 'id name<br/>'
    for stream in streams_list:
        streams += "<a href='/admin/streams/" + stream.id + "/packages/add'>" + stream.id + ' ' + stream.name + '</a><br/>'

    return streams


def get_packages(stream_id):
    packages_stream = PackagesStream.query(PackagesStream.id == stream_id).get()
    packages_list = []
    for package_id in packages_stream.packages_id_list:
        packages_list.append(PackageDictionary.query(PackageDictionary.id == package_id).get())

    packages = 'id name<br/>'
    for package in packages_list:
        packages += "<a href='/admin/streams/packages/" + package.id + "/words'>" + \
                    package.id + ' ' + package.name + "</a><br/>"

    return packages


class AddStreamHandler(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AddStreamHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/streamsscreen.html')
        self.response.write(
            template.render({'streams': get_streams(), "logout_link": users.create_logout_url('/')}))

    def post(self, *args, **kwargs):
        if PackagesStream.query(PackagesStream.id == self.request.get('stream_id')).get() is None:
            PackagesStream(id=self.request.get('stream_id'), name=self.request.get('stream_name'),
                           packages_id_list=[]).put()

        self.redirect('/admin/streams')


class AddPackageHandler(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AddPackageHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/packagesscreen.html')
        stream_id = kwargs.get('stream_id')
        self.response.write(template.render({'packages': get_packages(stream_id), 'stream_id': stream_id}))

    def post(self, **kwargs):
        if PackageDictionary.query(PackageDictionary.id == self.request.get('package_id')).get() is None:
            PackageDictionary(id=self.request.get('package_id'), name=self.request.get('package_name'),
                              release_time=int(self.request.get('release_time')), words=[]).put()

        stream = PackagesStream.query(PackagesStream.id == kwargs.get('stream_id')).get()
        if self.request.get('package_id') not in stream.packages_id_list:
            stream.packages_id_list.append(self.request.get('package_id'))
        stream.put()
        self.redirect('/admin/streams/' + kwargs.get('stream_id') + '/packages/add')


class ChangeWordsHandler(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ChangeWordsHandler, self).__init__(*args, **kwargs)

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
            self.response.write(
                template.render({'package_id': kwargs.get('package_id'), 'words': words}))

    def post(self, **kwargs):
        words = self.request.get('text')
        list_word = []
        for word in words.strip().split('\n'):
            list_word.append(word.strip())

        package = PackageDictionary.query(PackageDictionary.id == kwargs.get('package_id')).get()
        package.words = list_word
        package.put()
        template = JINJA_ENVIRONMENT.get_template('templates/packagewordsscreen.html')
        self.response.write(template.render({'package_id': kwargs.get('package_id'), 'words': words}))