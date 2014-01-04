__author__ = 'nikolay'
import random
import json
from google.appengine.ext import ndb

from all_handler import AllHandler
from objects.pregame import PreGame


class PreGameCreateHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameCreateHandler, self).set_device_id(**kwargs)
        game = json.loads(self.request.get('json'))
        game['pin'] = str(random.randint(100000000, 999999999))
        if 'version' not in game:
            game['version'] = 0
        for player in game['players']:
            player['last_update'] = game['version']
        game['words_last_update'] = game['version']
        game['order_last_update'] = game['version']
        game['settings']['last_update'] = game['version']
        game['players_deleted'] = []
        game_db = PreGame(game_json=json.dumps(game), device_ids=[self.device_id], pin=game['pin'], can_update=True)
        key = game_db.put()
        self.response.write(json.dumps({'id': key.urlsafe(), 'pin': game['pin']}))


class PreGameHandler(AllHandler):
    def get(self, **kwargs):
        super(PreGameHandler, self).set_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        if self.device_id in game.device_ids:
            self.response.write(PreGame.delete_last_updates_from_json(game.game_json))
        else:
            self.error(403)


class PreGameUpdateHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameUpdateHandler, self).set_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        if self.device_id not in game.device_ids:
            self.error(403)
        elif not game.can_update:
            self.error(403)
        else:
            update = json.loads(self.request.get('json'))
            game_struct = json.loads(game.game_json)
            game_struct['version'] += 1
            if 'words_change' in update:
                game_struct['words_last_update'] = game_struct['version']
                game_struct['words'] = update['words_change']
            if 'settings_change' in update:
                game_struct['settings'] = update['settings_change']
                game_struct['settings']['last_update'] = game_struct['version']
            if 'players_change' in update:
                for player in update['players_change']:
                    found = False
                    for where in xrange(len(game_struct['players'])):
                        if player['id'] == game_struct['players'][where]['id']:
                            game_struct['players'][where] = player
                            game_struct['players'][where]['last_update'] = game_struct['version']
                            found = True
                    if not found:
                        game_struct['players'].append(player)
                        game_struct['players'][-1]['last_update'] = game_struct['version']
            if 'players_delete' in update:
                for player in update['players_delete']:
                    for was_player in game_struct['players']:
                        if player == was_player['id']:
                            game_struct['players'].remove(was_player)
                            game_struct['players_deleted'].append({'id': player,
                                                                   'last_update': game_struct['version']})
                            break
            if 'order_change' in update:
                game_struct['order_last_update'] = game_struct['version']
                game_struct['order'] = update['order_change']
            changed = False
            for player_id in game_struct['order']:
                found = False
                for player in game_struct['players']:
                    if player['id'] == player_id:
                        found = True
                if not found:
                    changed = True
                    game_struct['order'].remove(player_id)
            for player in game_struct['players']:
                if player['id'] not in game_struct['order']:
                    game_struct['order'].append(player['id'])
                    changed = True
            if changed:
                game_struct['order_last_update'] = game_struct['version']
            game.game_json = json.dumps(game_struct)
            game.put()
            self.response.write(PreGame.delete_last_updates_from_json(game.game_json))


class PreGameVersionHandler(AllHandler):
    def get(self, **kwargs):
        super(PreGameVersionHandler, self).set_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        if self.device_id in game.device_ids:
            game_struct = json.loads(game.game_json)
            self.response.write(json.dumps({'version': game_struct['version']}))
        else:
            self.error(403)


class PreGameSinceHandler(AllHandler):
    def get(self, **kwargs):
        super(PreGameSinceHandler, self).set_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        game_struct = json.loads(game.game_json)
        last_version = int(kwargs.get('version'))
        diff = {'version': game_struct['version']}
        if game_struct['settings']['last_update'] > last_version:
            diff['settings_change'] = game_struct['settings']
            del diff['settings_change']['last_update']
        if game_struct['order_last_update'] > last_version:
            diff['order_change'] = game_struct['order']
        if game_struct['words_last_update'] > last_version:
            diff['words_change'] = game_struct['words']
        diff['players_change'] = []
        for player in game_struct['players']:
            if player['last_update'] > last_version:
                diff['players_change'].append(player)
                del diff['players_change'][-1]['last_update']
        diff['players_delete'] = []
        for player_del in game_struct['players_deleted']:
            if player_del['last_update'] > last_version:
                diff['players_delete'].append(player_del['id'])
        self.response.write(json.dumps(diff))


class PreGameStartHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameStartHandler, self).set_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        game.can_update = False
        game.put()


class PreGameAbortHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameAbortHandler, self).set_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        game.can_update = False
        game.put()


class PreGameJoinHandler(AllHandler):
    def post(self, **kwargs):
        super(PreGameJoinHandler, self).set_device_id(**kwargs)
        pin = str(self.request.get('json'))
        game = PreGame.query().filter(PreGame.pin == pin).get()
        if game is None:
            self.error(404)
        else:
            if not game.can_update:
                self.error(403)
            else:
                game.device_ids.append(self.device_id)
                key_db = game.put()
                response_struct = {"key": key_db.urlsafe(),
                                   "game": PreGame.delete_last_updates_from_json(game.game_json)}
                self.response.write(json.dumps(response_struct))