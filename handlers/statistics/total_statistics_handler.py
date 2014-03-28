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
        GamesForPlayerObject = ndb.gql("SELECT * FROM GameCountForPlayersObject").fetch()
        a, b, c, d, e = [], [], [], [], []
        all_game_count = 0
        all_word_count = 0

        for index, i in enumerate(WordCountObject):
            all_word_count += i.count
            a.append((i.count / GameCountObject[index].count, i.date.strftime("%Y-%m-%d")))
        for i in GameCountObject:
            all_game_count += i.count
            b.append((i.count, i.date.strftime("%Y-%m-%d")))
        for i in PlayerCountObject:
            c.append((i.count, i.date.strftime("%Y-%m-%d")))
        for index, i in enumerate(GameCountObject):
            d.append((GameLenObject[index].time / i.count / 1000 / 60, i.date.strftime("%Y-%m-%d")))
        for i in GamesForTimeObject:
            e.append((i.count, i.time))
        toPieLess2, toPie3_4, toPie5_10, toPieMore10 = 0, 0, 0, 0
        for index, i in enumerate(GamesForPlayerObject):
            if i.player_count <= 2:
                toPieLess2 += i.count
            elif i.player_count <= 4:
                toPie3_4 += i.count
            elif i.player_count <= 10:
                toPie5_10 += i.count
            else:
                toPieMore10 += i.count

        self.draw_page("statistics/total_statistic",
                       word_count_for_date=a,
                       game_count_for_date=b,
                       player_count_for_date=c,
                       average_game_time=d,
                       games_for_time=e,
                       p0=toPieLess2, p1=toPie3_4, p2=toPie5_10, p3=toPieMore10, all_word=all_word_count, all_game=all_game_count)
