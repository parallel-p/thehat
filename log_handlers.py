import webapp2
import json
from google.appengine.ext import ndb
from log_classes import *

'''
rounds_json:
{
rounds: [
    {
        "explain_player": "vasya",
        "guess_player": "petya"
        "word": {
            "text": "hat"
            "state" : 1
            "time_sec": 4.3
            "tries": 2
    },
    {
        "explain_player": "petya",
        "guess_player": "masha"
        "word": {
            "text": "hat"
            "state" : 2
            "time_sec": None
            "tries": None
    }
]
}
'''

# word states: GUESSED, NOT_GUESSED, FAILED = range(3)


class UpdateLog(webapp2.RequestHandler):
    def post(self, game_id):
        #log = Log.query(Log.game_id is not None and Log.game_id == game_id).fetch(1)
        log = Log.get_by_id(game_id)
        if log is None:
            log = Log(None, [], id=game_id)
        new_rounds = json.loads(self.request.get("rounds_json"))
        for _round in new_rounds.rounds:
            word = _round["word"]
            new_word = Word(word["text"], word["state"], word["time_sec"], word["tries"])
            new_round = Round(_round["guess_player"], _round["explain_player"], new_word)
            log.add_round(new_round)
        log.put()


class CalcResults(webapp2.RequestHandler):
    def get(self, game_id):
        log = Log.query(Log.game_id == game_id).fetch(1)
        if log is None:
            return #send to device exception "game isn't exist"
        return
    #doing nothing for a while