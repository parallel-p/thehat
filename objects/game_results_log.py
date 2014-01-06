__author__ = 'nikolay'

from google.appengine.ext import ndb


class Results(ndb.Model):
    results_json = ndb.JsonProperty(indexed=True)
    players_ids = ndb.StringProperty(repeated=True)
    timestamp = ndb.IntegerProperty()
    is_public = ndb.BooleanProperty()


class StatisticVersion(ndb.Model):
    version = ndb.IntegerProperty()


class GameLog(ndb.Model):
    json = ndb.StringProperty(indexed=False)
    game_id = ndb.StringProperty()
    last_statistic = ndb.IntegerProperty()
