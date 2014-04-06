from google.appengine.ext import ndb
from objects.user_devices import OwnedModel


def validate_word(prop, value):
    return value.strip().lower()


class UserDictionaryWord(OwnedModel):
    word = ndb.StringProperty(validator=validate_word)
    status = ndb.StringProperty(default="")
    dictionary = ndb.IntegerProperty(indexed=False, default=0)
    used = ndb.IntegerProperty(indexed=False, default=0)
    added = ndb.IntegerProperty(indexed=False, default=0)
    version = ndb.IntegerProperty(default=0)
