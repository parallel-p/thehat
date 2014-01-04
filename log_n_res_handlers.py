import webapp2
import json
from google.appengine.ext import ndb
#from log_classes import *
from all_handler import AllHandler
from objects.user_devices import get_user_by_device
from datetime import datetime

# word states: GUESSED, NOT_GUESSED, FAILED = range(3)


class Results(ndb.Model):
    results_json = ndb.JsonProperty()
    players_ids = ndb.StringProperty(repeated=True)
    timestamp = ndb.IntegerProperty()

    #def __init__(self, results_json, players_ids, **kwargs):
    #    super(Results, self).__init__(kwargs)
    #    self.results_json = results_json
    #    self.players_ids = players_ids
    #    self.timestamp = int(datetime.now().timestamp())


class UploadLog(AllHandler):
    def post(self, **kwargs):
        super(UploadLog, self).set_device_id(**kwargs)
        game_id = kwargs["game_id"]
        log_json = ndb.JsonProperty(id=game_id)
        log_json = self.request.get("log")
        log_json.put()


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
        results.put()


class CheckAnyResults(AllHandler):
    def get(self, **kwargs):
        player_id = get_user_by_device(self.device_id)
        timestamp = kwargs["timestamp"]
        results = Results.query(Results.players_ids.IN([player_id]),
                                Results.timestamp > timestamp).fetch(projection=["results_json"])
        #if len(results) == 0:
        #    self.error(401)  # have no access
        #    return
        response = [{'result': result.json, 'timestamp': datetime.now().timestamp()} for result in results]
        self.response.write(json.dumps(response))


class GetResults(AllHandler):
    def get(self, **kwargs):
        game_id = kwargs["game_id"]
        result = ndb.Key(Results, game_id).get()
        if result is None:
            self.error(404)  # results not found
            return
        self.response.write(result.results_json)