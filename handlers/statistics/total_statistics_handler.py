__author__ = 'ivan'

import webapp2
import logging

from handlers.base_handlers.web_request_handler import WebRequestHandler
from handlers.statistics.update_mathplotlib_plots import Plot
from google.appengine.ext import ndb
from objects.total_statistics_object import *
from handlers.base_handlers.api_request_handlers import APIRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord

class ScattedPlotHandler(APIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(ScattedPlotHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        N = kwargs.get("N")
        self.response.headers['Content-Type'] = "image/png"
        plot = ndb.Key(Plot, "scatter_plot_" +N).get()
        if plot is not None:
            self.response.write(plot.plot)
        else:
            self.response.write(None)


class HeatmapPlotHandler(APIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(HeatmapPlotHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        N = kwargs.get("N")
        self.response.headers['Content-Type'] = "image/png"
        plot = ndb.Key(Plot, "heatmap_plot_"+N).get()
        if plot is not None:
            self.response.write(plot.plot)
        else:
            self.response.write(None)


class DPlotHandler(APIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(DPlotHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        self.response.headers['Content-Type'] = "image/png"
        plot = ndb.Key(Plot, "d_plot").get()
        if plot is not None:
            self.response.write(plot.plot)
        else:
            self.response.write(None)


class TotalStatisticsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(TotalStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        daily_statistics = DailyStatistics.query().order(DailyStatistics.date).fetch()
        total = TotalStatistics.get()
        games_for_player_count = GamesForPlayerCount.query().order(GamesForPlayerCount.player_count).fetch()
        a, b, c, d = [], [], [], []

        for el in daily_statistics:
            a.append((el.words_used // el.games, el.date.strftime("%Y-%m-%d")))
            b.append((el.games, el.date.strftime("%Y-%m-%d")))
            c.append((el.players_participated, el.date.strftime("%Y-%m-%d")))
            d.append((round(el.total_game_duration / el.games / 60.0, 2), el.date.strftime("%Y-%m-%d")))
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
        logging.debug(total.by_hour)
        by_hour = [0 for i in range(24)]
        by_day = [0 for i in range(7)]
        for hour, games in enumerate(total.by_hour):
            by_hour[hour % 24] += games
            by_day[(hour // 24 + 3) % 7] += games
        words_in_dictionary = GlobalDictionaryWord.query().count()
        self.draw_page("statistics/total_statistic",
                       word_count_for_date=a,
                       game_count_for_date=b,
                       player_count_for_date=c,
                       average_game_time=d,
                       games_for_time=total.by_hour,
                       by_hour=by_hour,
                       by_day=by_day,
                       player_count=player_count_classes, all_word=total.words_used,
                       all_game=total.games, words_in_dictionary=words_in_dictionary)
