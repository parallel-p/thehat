__author__ = 'ivan'

from google.appengine.ext import db


class GlobalDictionaryWord(db.Model):
    word = db.StringProperty(indexed=False)
    E = db.IntegerProperty()
    D = db.IntegerProperty()
    tags = db.StringProperty(indexed=False)