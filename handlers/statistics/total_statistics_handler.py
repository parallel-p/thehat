__author__ = 'ivan'

import webapp2

from handlers.base_handlers.web_request_handler import WebRequestHandler
from handlers.statistics.update_mathplotlib_plots import Plot
from google.appengine.ext import ndb
from objects.total_statistics_object import *

class ScattedPlotHandler(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = "image/png"
        plot = ndb.Key(Plot, "scatter_plot").get()
        if plot is not None:
            self.response.write(plot.plot)
        else:
            self.response.write(None)


class HeatmapPlotHandler(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = "image/png"
        plot = ndb.Key(Plot, "heatmap_plot").get()
        if plot is not None:
            self.response.write(plot.plot)
        else:
            self.response.write(None)


class TotalStatisticsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(TotalStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        daily_statistics = DailyStatistics.query().order(DailyStatistics.date).fetch()
        games_for_hour = GamesForHour.query().order(GamesForHour.hour).fetch()
        games_for_player_count = GamesForPlayerCount.query().order(GamesForPlayerCount.player_count).fetch()
        a, b, c, d, e = [], [], [], [], []
        all_game_count = 0
        all_word_count = 0

        for el in daily_statistics:
            all_word_count += el.words_used
            a.append((el.words_used // el.games, el.date.strftime("%Y-%m-%d")))
            all_game_count += el.games
            b.append((el.games, el.date.strftime("%Y-%m-%d")))
            c.append((el.players_participated, el.date.strftime("%Y-%m-%d")))
            d.append((round(el.total_game_duration / el.games / 60.0, 2), el.date.strftime("%Y-%m-%d")))
        for el in games_for_hour:
            e.append((el.games, el.hour))
        player_count_classes = [0, 0, 0, 0]
        for el in games_for_player_count:
            if el.player_count <= 2:
                player_count_classes[0] += el.games
            elif el.player_count <= 4:
                player_count_classes[1] += el.games
            elif el.player_count <= 10:
                player_count_classes[2] += el.games
            else:
                player_count_classes[3] += el.games


        self.draw_page("statistics/total_statistic",
                       word_count_for_date=a,
                       game_count_for_date=b,
                       player_count_for_date=c,
                       average_game_time=d,
                       games_for_time=e,
                       player_count=player_count_classes, all_word=all_word_count,
                       all_game=all_game_count)
