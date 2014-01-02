__author__ = 'ivan'

from google.appengine.ext import ndb


class ComplainedWord(ndb.Model):
    device_id = ndb.StringProperty()
    word = ndb.StringProperty()
    cause = ndb.IntegerProperty()
    replacement_word = ndb.StringProperty()