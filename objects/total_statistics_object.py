__author__ = 'ivan'

from google.appengine.ext import ndb


class DailyStatistics(ndb.Model):
    date = ndb.DateTimeProperty()
    words_used = ndb.IntegerProperty(default=0)
    players_participated = ndb.IntegerProperty(default=0)
    games = ndb.IntegerProperty(default=0)
    total_game_duration = ndb.IntegerProperty(default=0)


class GamesForHour(ndb.Model):
    games = ndb.IntegerProperty(default=0)
    hour = ndb.IntegerProperty()


class GamesForPlayerCount(ndb.Model):
    games = ndb.IntegerProperty(default=0)
    player_count = ndb.IntegerProperty()
