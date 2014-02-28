from google.appengine.ext import ndb
from objects.user_devices import OwnedModel


class UserDictionaryWord(OwnedModel):
    word = ndb.StringProperty()
    status = ndb.StringProperty(indexed=False, default="")
    dictionary = ndb.IntegerProperty(indexed=False, default=0)
    used = ndb.IntegerProperty(indexed=False, default=0)
    added = ndb.IntegerProperty(indexed=False, default=0)
    version = ndb.IntegerProperty(default=0)
