__author__ = 'ivan'

from google.appengine.ext import ndb
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
import math
import datetime


class GameLength(ndb.Model):
    player_count = ndb.IntegerProperty()
    lens = ndb.JsonProperty()
    type = ndb.StringProperty()


class GameLenPredictionHandler(AdminRequestHandler):

    @staticmethod
    def count_expected_value(game):
        total_time = 0
        for i in game.lens:
            total_time += int(i) / 1000
        return int(total_time / len(game.lens))

    @staticmethod
    def count_dispersion(game):
        expected = GameLenPredictionHandler.count_expected_value(game)
        dispersion = 0
        for i in game.lens:
            dispersion += (int(i) / 1000 - expected)**2
        return int(math.sqrt(dispersion / len(game.lens)))

    def __init__(self, *args, **kwargs):
        super(GameLenPredictionHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        games = ndb.gql("SELECT * FROM GameLength").fetch()
        elems = []
        for game in games:
            expected = datetime.datetime.fromtimestamp(self.count_expected_value(game)).strftime('%H:%M:%S')
            dispersion = datetime.datetime.fromtimestamp(self.count_dispersion(game)).strftime('%H:%M:%S')
            elems.append((game.player_count, expected, dispersion))
        elems.sort()
        self.draw_page('statistics/prediction_handler', elems=elems)
