__author__ = 'ivan'

import webapp2

from environment import *
from handlers.base_handlers.web_request_handler import WebRequestHandler
from google.appengine.ext import ndb
import collections
import datetime


class TotalStatisticsHandler(WebRequestHandler):


    def __init__(self, *args, **kwargs):
        super(TotalStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        WordCountObject= ndb.gql("SELECT * FROM WordCountObject ORDER BY date").fetch()
        GameCountObject = ndb.gql("SELECT * FROM GameCountObject ORDER BY date").fetch()
        PlayerCountObject = ndb.gql("SELECT * FROM PlayerCountObject ORDER BY date").fetch()
        GameLenObject = ndb.gql("SELECT * FROM GameLenObject ORDER BY date").fetch()
        GamesForTimeObject = ndb.gql("SELECT * FROM GamesForTimeObject ORDER BY time").fetch()
        a, b, c, d, e = [], [], [], [], []
        for i in WordCountObject:
            a.append((i.count, i.date.strftime("%Y-%m-%d")))
        for i in GameCountObject:
            b.append((i.count, i.date.strftime("%Y-%m-%d")))
        for i in PlayerCountObject:
            c.append((i.count, i.date.strftime("%Y-%m-%d")))
        for index, i in enumerate(GameCountObject):
            d.append((GameLenObject[index].time / i.count, i.date.strftime("%Y-%m-%d")))
        for i in GamesForTimeObject:
            e.append((i.count, i.time))

        self.draw_page("statistics/total_statistic",
                       word_count_for_date=a,
                       game_count_for_date=b,
                       player_count_for_date=c,
                       average_game_time=d,
                       games_for_time=e)

total_statistics_routes = [
    webapp2.Route('/statistics/total_statistics',
                  handler=TotalStatisticsHandler,
                  name="total statistics handler")
]