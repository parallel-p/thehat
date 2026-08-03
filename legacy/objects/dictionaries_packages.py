from google.appengine.ext import ndb


class PackagesStream(ndb.Model):
    id = ndb.StringProperty()
    name = ndb.StringProperty()
    packages_id_list = ndb.StringProperty(repeated=True)


class PackageDictionary(ndb.Model):
    id = ndb.StringProperty()
    name = ndb.StringProperty()
    release_time = ndb.IntegerProperty()
    words = ndb.StringProperty(repeated=True)