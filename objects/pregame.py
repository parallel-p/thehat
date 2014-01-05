__author__ = 'nikolay'

import json

from google.appengine.ext import ndb


class PreGame(ndb.Model):
    game_json = ndb.StringProperty(indexed=False)
    device_ids = ndb.StringProperty(repeated=True)
    pin = ndb.StringProperty()
    can_update = ndb.BooleanProperty()

    @staticmethod
    def delete_last_updates_from_json(json_string):
        game = json.loads(json_string)
        del game['words_last_update']
        del game['order_last_update']
        del game['meta']['last_update']
        for player in game['players']:
            del player['last_update']
        del game['players_deleted']
        return json.dumps(game)