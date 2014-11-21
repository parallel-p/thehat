import constants

__author__ = 'ivan'

from google.appengine.ext import ndb, db
from google.appengine.api import memcache


class WordLookup(ndb.Model):
    proper_word = ndb.StringProperty(required=True)


class GlobalDictionaryWord(ndb.Model):
    cnt = ndb.IntegerProperty()
    timestamp = ndb.DateTimeProperty(auto_now=True)
    word = ndb.StringProperty(indexed=True)
    E = ndb.FloatProperty(default=50.0)
    D = ndb.FloatProperty(default=50.0/3)
    used_times = ndb.IntegerProperty(default=0)
    guessed_times = ndb.IntegerProperty(default=0)
    failed_times = ndb.IntegerProperty(default=0)
    total_explanation_time = ndb.IntegerProperty(default=0)
    counts_by_expl_time = ndb.JsonProperty(default=[])
    used_games = ndb.StringProperty(indexed=False, repeated=True)
    tags = ndb.StringProperty(indexed=False)
    danger = ndb.ComputedProperty(lambda self: (self.failed_times / self.used_times) if self.used_times != 0 else 0)
    deleted = ndb.BooleanProperty(default=False)

    @staticmethod
    def get(word):
        word = word.lower()
        proper_word = memcache.get(u"word_lookup_{}".format(word)) or word
        entity = ndb.Key(GlobalDictionaryWord, proper_word).get()
        if entity:
            return entity
        proper_word = ndb.Key(WordLookup, word).get()
        if not proper_word:
            return None
        proper_word = proper_word.proper_word
        memcache.set(u"word_lookup_{}".format(word), proper_word, time=60*60*12)
        return ndb.Key(GlobalDictionaryWord, proper_word).get()


class GlobalDictionaryVersion(db.Model):
    version = db.IntegerProperty()

    @staticmethod
    def get_server_version():
        version = GlobalDictionaryVersion.get_by_key_name(constants.version_key)
        return 0 if version is None else int(version.version)

    @staticmethod
    def update_version():
        version = GlobalDictionaryVersion.get_by_key_name(constants.version_key)
        if version is None:
            version = GlobalDictionaryVersion(key_name=constants.version_key, version=1)
        else:
            version.version += 1
        version.put()
