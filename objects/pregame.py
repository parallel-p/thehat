__author__ = 'nikolay'

from google.appengine.ext import ndb
import json


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

    @staticmethod
    def abort_game(game_id):
        key_db = ndb.Key(urlsafe=game_id)
        game = key_db.get()
        if not game.can_update:
            return
        game.can_update = False
        game.put()


class CurrentGame(ndb.Model):
    device_id = ndb.StringProperty()
    game_id = ndb.StringProperty()
    is_owner = ndb.BooleanProperty()

    @staticmethod
    def set_current_game(device_id, game_id, is_owner=False):
        cur_game = CurrentGame.query(CurrentGame.device_id == device_id).get()
        if cur_game is None:
            cur_game = CurrentGame(device_id=device_id, game_id=game_id, is_owner=is_owner)
        else:
            if cur_game.is_owner:
                PreGame.abort_game(cur_game.game_id)
            cur_game.game_id = game_id
            cur_game.is_owner = is_owner
        cur_game.put()

    @staticmethod
    def get_current_game(device_id):
        cur_game = CurrentGame.query(CurrentGame.device_id == device_id).get()
        if cur_game is None:
            return None
        else:
            return cur_game.game_id