import json
import time

from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from all_handler import AllHandler
from objects.user_devices import get_user_by_device
from objects.game_results_log import GameLog, Results


def make_timestamp():
    return int(1000 * time.time())


class UploadLog(AllHandler):
    def post(self, **kwargs):
        super(UploadLog, self).set_device_id(**kwargs)
        game_id = kwargs["game_id"]
        game_on_server = GameLog.query(GameLog.game_id == game_id).get()
        if game_on_server is not None:
            self.response.write("OK, already exist")
        else:
            log = GameLog(game_id=game_id, json=self.request.get("json"))
            log.put()
            taskqueue.add(url='/internal/add_game_to_statistic', params={'game_id': game_id})
            self.response.write("OK, added")


class UploadRes(AllHandler):
    def post(self, **kwargs):
        super(UploadRes, self).set_device_id(**kwargs)
        game_id = kwargs.get("game_id")
        results = ndb.Key(Results, game_id).get()
        if results is not None:
            self.error(403)  # you have no access to rewrite results
            return
        req_json = json.loads(self.request.get("json"))

        results_json = json.dumps(req_json['results'])
        is_public = req_json['is_public']
        key = ndb.Key(urlsafe=game_id)
        if key.kind() == 'PreGame':
            pregame = key.get()
            settings = json.loads(pregame.game_json)['meta']
            is_public = is_public or settings['is_public']
            devices = pregame.device_ids
        else:
            devices = [self.device_id]
        players_ids = [get_user_by_device(device) for device in devices]
        results = Results(id=game_id)
        results.results_json = results_json
        results.players_ids = players_ids
        results.timestamp = make_timestamp()
        results.is_public = is_public
        results.put()


class CheckAnyResults(AllHandler):
    def get(self, **kwargs):
        super(CheckAnyResults, self).set_device_id(**kwargs)
        player_id = get_user_by_device(self.device_id)
        timestamp = kwargs["timestamp"]
        results = Results.query(Results.players_ids.IN([player_id]),
                                Results.timestamp > int(timestamp)).fetch(projection=["results_json"])
        response = {'results':[result.results_json for result in results],
                    'timestamp':make_timestamp()}
        self.response.write(json.dumps(response))


class GetResults(AllHandler):
    def get(self, **kwargs):
        super(GetResults, self).set_device_id(**kwargs)
        game_id = kwargs["game_id"]
        result = ndb.Key(Results, game_id).get()
        if result is None:
            self.error(404)  # results not found
            return
        if not result.is_public and not get_user_by_device(self.device_id) in result.players_ids:
            self.error(403)  # you have no access to this game
            return
        self.response.write(result.results_json)