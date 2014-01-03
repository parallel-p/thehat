__author__ = 'ivan'

from google.appengine.ext import db


class ComplainedWord(db.Model):
    device_id = db.StringProperty()
    word = db.StringProperty()
    reason = db.StringProperty()
    replacement_word = db.StringProperty()


"typo"
"non_noun"
"non_dict"
"loanword"