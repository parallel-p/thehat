__author__ = 'nikolay'

from google.appengine.ext import ndb


class Results(ndb.Model):
    results_json = ndb.StringProperty(indexed=True)
    players_ids = ndb.StringProperty(repeated=True)
    timestamp = ndb.IntegerProperty()
    is_public = ndb.BooleanProperty()


class StatisticVersion(ndb.Model):
    version = ndb.IntegerProperty()


class NonFinishedGame(ndb.Model):
    log = ndb.StringProperty()
    players_ids = ndb.StringProperty(repeated=True)

class GameLog(ndb.Model):
    json = ndb.JsonProperty()
    last_statistic = ndb.IntegerProperty()