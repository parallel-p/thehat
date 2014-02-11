from google.appengine.ext import ndb


class UserDictionaryWord(ndb.Model):
    word = ndb.StringProperty()
    status = ndb.StringProperty(indexed=False, default="")
    dictionary = ndb.IntegerProperty(indexed=False, default=0)
    version = ndb.IntegerProperty(default=0)
