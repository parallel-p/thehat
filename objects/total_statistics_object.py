__author__ = 'ivan'

from google.appengine.ext import ndb


class WordCountObject(ndb.Model):
    count = ndb.IntegerProperty()
    date = ndb.DateProperty()


class PlayerCountObject(ndb.Model):
    count = ndb.IntegerProperty()
    date = ndb.DateProperty()


class GameCountObject(ndb.Model):
    count = ndb.IntegerProperty()
    date = ndb.DateProperty()


class GameLenObject(ndb.Model):
    time = ndb.IntegerProperty()
    date = ndb.DateProperty()


class GamesForTimeObject(ndb.Model):
    count = ndb.IntegerProperty()
    time = ndb.IntegerProperty()


class GameTimeForPlayersObject(ndb.Model):
    time = ndb.IntegerProperty()
    player_count = ndb.IntegerProperty()


class GameCountForPlayersObject(ndb.Model):
    count = ndb.IntegerProperty()
    player_count = ndb.IntegerProperty()
