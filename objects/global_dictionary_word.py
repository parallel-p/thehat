__author__ = 'ivan'

from google.appengine.ext import db


class GlobalDictionaryWord(db.Expando):
    word = db.StringProperty()
    E = db.FloatProperty()
    D = db.FloatProperty()
    tags = db.StringProperty(indexed=False)