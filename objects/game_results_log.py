__author__ = 'nikolay'

from google.appengine.ext import ndb


class Results(ndb.Model):
    results_json = ndb.StringProperty(indexed=False)
    players_ids = ndb.KeyProperty(repeated=True)
    timestamp = ndb.IntegerProperty()
    is_public = ndb.BooleanProperty()


class StatisticVersion(ndb.Model):
    version = ndb.IntegerProperty()


class SavedGame(ndb.Model):
    log = ndb.TextProperty()


class GameLog(ndb.Model):
    json = ndb.StringProperty(indexed=False)
    last_statistic = ndb.IntegerProperty()
