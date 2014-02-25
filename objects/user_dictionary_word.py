from google.appengine.ext import ndb
from objects.user_devices import DeviceSpecificModel


class UserDictionaryWord(DeviceSpecificModel):
    word = ndb.StringProperty()
    status = ndb.StringProperty(indexed=False, default="")
    dictionary = ndb.IntegerProperty(indexed=False, default=0)
    version = ndb.IntegerProperty(default=0)
