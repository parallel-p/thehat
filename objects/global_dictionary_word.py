__author__ = 'ivan'

from google.appengine.ext import ndb


class GlobalDictionaryWord(ndb.Model):
    cnt = ndb.IntegerProperty()
    word = ndb.StringProperty()
    E = ndb.FloatProperty()
    D = ndb.FloatProperty()
    tags = ndb.StringProperty(indexed=False)