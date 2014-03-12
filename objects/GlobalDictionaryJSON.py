__author__ = 'ivan'

from google.appengine.ext import ndb


class GlobalDictionaryJson(ndb.Model):
    json = ndb.TextProperty()
    timestamp = ndb.IntegerProperty(indexed=True)