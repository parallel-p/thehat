__author__ = 'nikolay'

from google.appengine.ext import ndb
import json


class PreGame(ndb.Model):
    game_json = ndb.StringProperty(indexed=False)
    device_ids = ndb.StringProperty(repeated=True)
    pin = ndb.IntegerProperty()
    can_update = ndb.BooleanProperty()

    @staticmethod
    def delete_last_updates_from_json(json_string):
        game = json.loads(json_string)
        del game['words_last_update']
        del game['order_last_update']
        del game['settings']['last_update']
        for player in game['players']:
            del player['last_update']
        return json.dumps(game)