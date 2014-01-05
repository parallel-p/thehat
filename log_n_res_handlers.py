import webapp2
import json
from google.appengine.ext import ndb
#from log_classes import *
from all_handler import AllHandler
from objects.user_devices import get_user_by_device
import time

# word states: GUESSED, NOT_GUESSED, FAILED = range(3)


def make_timestamp():
    return int(1000*time.time())


class Results(ndb.Model):
    results_json = ndb.JsonProperty(indexed=True)
    players_ids = ndb.StringProperty(repeated=True)
    timestamp = ndb.IntegerProperty()


class Log(ndb.Model):
    json = ndb.JsonProperty()


class UploadLog(AllHandler):
    def post(self, **kwargs):
        super(UploadLog, self).set_device_id(**kwargs)
        game_id = kwargs["game_id"]
        log = Log(id=game_id)
        log.json = self.request.get("log")
        log.put()


class UploadRes(AllHandler):
    def post(self, **kwargs):
        super(UploadRes, self).set_device_id(**kwargs)
        game_id = kwargs.get("game_id")
        results = ndb.Key(Results, game_id).get()
        if results is not None:
            return
        results_json = self.request.get("results")
        key = ndb.Key(urlsafe=game_id)
        if key.kind() == 'PreGame':
            devices = key.get().device_ids
        else:
            devices = [self.device_id]
        players_ids = [get_user_by_device(device) for device in devices]
        results = Results(id=game_id)
        results.results_json = results_json
        results.players_ids = players_ids
        results.timestamp = make_timestamp()
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
        game_id = kwargs["game_id"]
        result = ndb.Key(Results, game_id).get()
        if result is None:
            self.error(404)  # results not found
            return
        self.response.write(result.results_json)