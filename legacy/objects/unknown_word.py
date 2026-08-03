__author__ = 'ivan'

from google.appengine.ext import ndb


class UnknownWord(ndb.Model):

    times_used = ndb.IntegerProperty(default=0)
    ignored = ndb.BooleanProperty(default=False)
    word = ndb.StringProperty()