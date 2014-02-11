__author__ = 'ivan'

from google.appengine.ext import ndb


class ComplainedWord(ndb.Model):
    device = ndb.KeyProperty()
    word = ndb.StringProperty()
    reason = ndb.StringProperty()
    replacement_word = ndb.StringProperty()


"typo"
"non_noun"
"non_dict"
"loanword"