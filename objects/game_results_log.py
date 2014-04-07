__author__ = 'nikolay'

from google.appengine.ext import ndb
from objects.enum_property import EnumProperty


class Results(ndb.Model):
    results_json = ndb.StringProperty(indexed=False)
    players_ids = ndb.KeyProperty(repeated=True)
    timestamp = ndb.IntegerProperty()
    is_public = ndb.BooleanProperty()


class StatisticVersion(ndb.Model):
    version = ndb.IntegerProperty()


class SavedGame(ndb.Model):
    log = ndb.TextProperty()

IGNORE_REASON = {
    'old_version': "This game log was created by old version of the application and is not supported",
    'suspect_too_quick_explanation': "Most of the words in this game were explained too quickly.",
    'suspect_too_little_words': "Too little of words used in this game were explained",
    'format-error': "Log of this game isn't formatted properly",
    'not_hat': "This is not an original hat game",
    'aborted': "This game was aborted on device",
    'manual': "This game was marked as ignored by administrator"
}


class GameLog(ndb.Model):
    json = ndb.StringProperty(indexed=False)
    ignored = ndb.BooleanProperty(default=False)
    reason = EnumProperty(IGNORE_REASON)
