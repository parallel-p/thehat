__author__ = 'ivan'

from google.appengine.ext import ndb


class DailyStatistics(ndb.Model):
    date = ndb.DateTimeProperty()
    words_used = ndb.IntegerProperty(default=0)
    players_participated = ndb.IntegerProperty(default=0)
    games = ndb.IntegerProperty(default=0)
    total_game_duration = ndb.IntegerProperty(default=0)


class TotalStatistics(ndb.Model):
    games = ndb.IntegerProperty(default=0)
    words_used = ndb.IntegerProperty(default=0)
    by_hour = ndb.JsonProperty(default=[0 for i in range(24*7)])

    @classmethod
    def get(cls):
        return ndb.Key(cls, 'total_statistics').get() or TotalStatistics(id='total_statistics')


class GamesForPlayerCount(ndb.Model):
    games = ndb.IntegerProperty(default=0)
    player_count = ndb.IntegerProperty()
