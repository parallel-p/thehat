__author__ = 'ivan'

from google.appengine.ext import db


class GlobalDictionaryWord(db.Expando):
    word = db.StringProperty()
    E = db.IntegerProperty()
    D = db.IntegerProperty()