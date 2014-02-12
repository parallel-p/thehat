__author__ = 'ivan'

from google.appengine.ext import ndb


class GlobalDictionaryWord(ndb.Model):
    word = ndb.StringProperty()
    E = ndb.FloatProperty()
    D = ndb.FloatProperty()
    tags = ndb.StringProperty(indexed=False)