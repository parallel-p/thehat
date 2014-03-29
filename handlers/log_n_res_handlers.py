__author__ = 'konstantin'
import json
import time

from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from objects.user_devices import get_device_and_user
from objects.pin_number import PinNumber
from objects.game_results_log import GameLog, Results, SavedGame
from base_handlers.api_request_handlers import APIRequestHandler, AuthorizedAPIRequestHandler


def make_timestamp():
    return int(1000 * time.time())


class GameLogHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GameLogHandler, self).__init__(*args, **kwargs)

    def put(self, **kwargs):
        game_id = json.loads(self.request.body)['setup']['meta']['game.id']
        game_key = ndb.Key(GameLog, game_id).get()
        if game_key is None:
            log = GameLog(json=self.request.body, id=game_id)
            log.put()
            taskqueue.add(url='/internal/add_game_to_statistic', params={'game_id': game_id}, countdown=5)
        self.response.set_status(201)


class GameResultsHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GameResultsHandler, self).__init__(*args, **kwargs)

    def put(self, **kwargs):
        game_id = kwargs.get("game_id")
        results = ndb.Key(Results, game_id).get()
        if results is not None:
            self.abort(409)
        req_json = json.loads(self.request.body)

        results_json = json.dumps(req_json['results'])
        if 'is_public' in req_json:
            is_public = req_json['is_public']
        else:
            is_public = False
        key = ndb.Key(urlsafe=game_id)
        if key.kind() == 'PreGame':
            pregame = key.get()
            settings = json.loads(pregame.game_json)['meta']
            if 'is_public' in settings:
                is_public = is_public or settings['is_public']
            devices = pregame.device_ids
        else:
            devices = [self.device_id]
        players_ids = [get_device_and_user(device)[1] for device in devices]
        results = Results(id=game_id)
        results.results_json = results_json
        results.players_ids = players_ids
        results.timestamp = make_timestamp()
        results.is_public = is_public
        results.put()
        self.response.set_status(201)

    def get(self, **kwargs):
        game_id = kwargs["game_id"]
        result = ndb.Key(Results, game_id).get()
        if result is None:
            self.abort(404)
        if not result.is_public and not self.user_key in result.players_ids:
            self.abort(403)
        self.response.write(result.results_json)


class GameResultsUpdateHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GameResultsUpdateHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        timestamp = kwargs["timestamp"]
        results = Results.query(Results.players_ids == self.user_key,
                                Results.timestamp > int(timestamp))
        response = {'results': [result.results_json for result in results],
                    'timestamp': make_timestamp()}
        self.response.write(json.dumps(response))


class SaveGameHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(SaveGameHandler, self).__init__(*args, **kwargs)

    def post(self):
        log = self.request.get("json")
        game = SavedGame(log=log)
        game.put()
        pin = PinNumber.generate("savegame", data=game.key, lifetime=24*60*60)
        self.response.write(pin)
        self.response.set_status(201)

    def get(self, **kwargs):
        pin = PinNumber.retrive(kwargs["pin"], "savegame")
        if pin is None:
            self.error(404)
            return
        game = pin.data.get()
        self.response.write(game.log)
