__author__ = 'nikolay'
import random
import json
from google.appengine.ext import ndb

from objects.pregame import PreGame, CurrentGame
from base_handlers.api_request_handlers import APIRequestHandler


class PreGameCreateHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameCreateHandler, self).__init__(*args, **kwargs)

    def post(self, **kwargs):
        super(PreGameCreateHandler, self).get_device_id(**kwargs)
        game = json.loads(self.request.get('json'))
        game['pin'] = str(random.randint(100000000, 999999999))
        if 'version' not in game:
            game['version'] = 0
        for player in game['players']:
            player['last_update'] = game['version']
        game['words_last_update'] = game['version']
        game['order_last_update'] = game['version']
        game['meta']['last_update'] = game['version']
        game['players_deleted'] = []
        game_db = PreGame(game_json=json.dumps(game), device_ids=[self.device_id], pin=game['pin'], can_update=True)
        key = game_db.put()
        game['id'] = key.urlsafe()
        game_db.game_json = json.dumps(game)
        game_db.put()
        CurrentGame.set_current_game(self.device_id, key.urlsafe(), True)
        self.response.write(json.dumps({'id': key.urlsafe(), 'pin': game['pin'], 'version': game['version']}))


class PreGameHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        super(PreGameHandler, self).get_device_id(**kwargs)
        #TODO: but if we have incorrect game_id?
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        game_struct = json.loads(game.game_json)
        if self.device_id in game.device_ids:
            self.response.write(json.dumps({
                'id': key_db.urlsafe(),
                'version': game_struct['version'],
                'game': json.loads(PreGame.delete_last_updates_from_json(game.game_json))
            }))
        else:
            self.error(403)


class PreGameUpdateHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameUpdateHandler, self).__init__(*args, **kwargs)

    def post(self, **kwargs):
        super(PreGameUpdateHandler, self).get_device_id(**kwargs)
        #TODO: but if we have incorrect game_id?
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        if self.device_id not in game.device_ids:
            self.error(403)
        elif not game.can_update:
            self.response.write(json.dumps({
                'game_id': key_db.urlsafe(),
                'status': 'started',
                'version': json.loads(game.game_json)['version']
            }))
            self.error(410)
        else:
            update = json.loads(self.request.get('json'))
            game_struct = json.loads(game.game_json)
            game_struct['version'] += 1
            if 'updated_words' in update:
                game_struct['words_last_update'] = game_struct['version']
                game_struct['words'] = update['updated_words']
            if 'updated_meta' in update:
                game_struct['meta'] = update['updated_meta']
                game_struct['meta']['last_update'] = game_struct['version']
            if 'updated_players' in update:
                for player in update['updated_players']:
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
            if 'updated_order' in update:
                game_struct['order_last_update'] = game_struct['version']
                game_struct['order'] = update['updated_order']
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
            self.response.write(json.dumps({
                'id': key_db.urlsafe(),
                'version': game_struct['version'],
                'game': json.loads(PreGame.delete_last_updates_from_json(game.game_json))
            }))


class PreGameVersionHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameVersionHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        super(PreGameVersionHandler, self).get_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        if self.device_id in game.device_ids:
            game_struct = json.loads(game.game_json)
            self.response.write(json.dumps({'id': key_db.urlsafe(), 'version': game_struct['version']}))
        else:
            self.error(403)


class PreGameSinceHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameSinceHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        super(PreGameSinceHandler, self).get_device_id(**kwargs)
        key_db = ndb.Key(urlsafe=kwargs.get('game_id'))
        game = key_db.get()
        game_struct = json.loads(game.game_json)
        last_version = int(kwargs.get('version'))
        diff = {'version': game_struct['version']}
        if game_struct['meta']['last_update'] > last_version:
            diff['updated_meta'] = game_struct['meta']
            del diff['updated_meta']['last_update']
        if game_struct['order_last_update'] > last_version:
            diff['updated_order'] = game_struct['order']
        if game_struct['words_last_update'] > last_version:
            diff['updated_words'] = game_struct['words']
        diff['updated_players'] = []
        for player in game_struct['players']:
            if player['last_update'] > last_version:
                diff['updated_players'].append(player)
                del diff['updated_players'][-1]['last_update']
        diff['players_delete'] = []
        for player_del in game_struct['players_deleted']:
            if player_del['last_update'] > last_version:
                diff['players_delete'].append(player_del['id'])
        self.response.write(json.dumps({
            'id': key_db.urlsafe(),
            'version': diff['version'],
            'game': diff
        }))


class PreGameStartHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameStartHandler, self).__init__(*args, **kwargs)

    def post(self, **kwargs):
        super(PreGameStartHandler, self).get_device_id(**kwargs)
        PreGame.abort_game(kwargs.get('game_id'))


class PreGameAbortHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameAbortHandler, self).__init__(*args, **kwargs)

    def post(self, **kwargs):
        super(PreGameAbortHandler, self).get_device_id(**kwargs)
        PreGame.abort_game(kwargs.get('game_id'))


class PreGameJoinHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameJoinHandler, self).__init__(*args, **kwargs)

    def post(self, **kwargs):
        super(PreGameJoinHandler, self).get_device_id(**kwargs)
        pin = str(json.loads(self.request.get('json'))['pin'])
        game = PreGame.query().filter(PreGame.pin == pin).get()
        if game is None:
            self.error(404)
        else:
            if not game.can_update:
                self.response.write(json.dumps({
                    'game_id': game.key.urlsafe(),
                    'status': 'started',
                    'version': json.loads(game.game_json)['version']
                }))
                self.error(410)
            else:
                game.device_ids.append(self.device_id)
                key_db = game.put()
                game_struct = json.loads(game.game_json)
                CurrentGame.set_current_game(self.device_id, key_db.urlsafe())
                response_struct = {"id": key_db.urlsafe(),
                                   "version": game_struct['version'],
                                   "game": json.loads(PreGame.delete_last_updates_from_json(game.game_json))}
                self.response.write(json.dumps(response_struct))


class PreGameCurrentHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PreGameCurrentHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        super(PreGameCurrentHandler, self).get_device_id(**kwargs)
        game_id = CurrentGame.get_current_game(self.device_id)
        if game_id is None:
            self.response.write(json.dumps([]))
        else:
            self.response.write(json.dumps([game_id]))