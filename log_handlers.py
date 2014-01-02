import webapp2
import json
from google.appengine.ext import ndb
#from log_classes import *
from all_handler import AllHandler

# word states: GUESSED, NOT_GUESSED, FAILED = range(3)


class UploadRes(AllHandler):
    def get(self, **kwargs):
        super(UploadRes, self).set_device_id(**kwargs)
        log = self.request.get("log_json")
        results = self.request.get("results_json")
        game_id = kwargs.get("game_id")
        pregame = ndb.Key(urlsafe=game_id).get()
        if pregame is not None:
            devices = pregame.device_ids
        else:
            devices = [self.device_id]
        players = [ for device in devices]



class CalcResults(webapp2.RequestHandler):
    def get(self, game_id):
        log = Log.query(Log.game_id == game_id).fetch(1)
        if log is None:
            return #send to device exception "game isn't exist"
        return
    #doing nothing for a while