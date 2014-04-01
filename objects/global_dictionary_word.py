__author__ = 'ivan'

from google.appengine.ext import ndb


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