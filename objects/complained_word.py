__author__ = 'ivan'

from google.appengine.ext import db


class ComplainedWord(db.Model):
    device_id = db.StringProperty()
    word = db.StringProperty()
    cause = db.IntegerProperty()
    replacement_word = db.StringProperty()
