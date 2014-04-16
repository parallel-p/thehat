__author__ = 'ivan'

from google.appengine.api import memcache

from handlers.base_handlers.web_request_handler import WebRequestHandler
from handlers.statistics.update_mathplotlib_plots import Plot
from objects.total_statistics_object import *
from handlers.base_handlers.api_request_handlers import APIRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord


class ScattedPlotHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ScattedPlotHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        N = kwargs.get("N")
        self.response.headers['Content-Type'] = "image/png"
        plot = ndb.Key(Plot, "scatter_plot_" + N).get()
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
        plot = ndb.Key(Plot, "heatmap_plot_" + N).get()
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


def cache(key, func):
    key = '{}_total_statistics'.format(key)
    val = memcache.get(key)
    if not val:
        val = func()
        memcache.set(key=key, value=val, time=60 * 60)
    return val


class TotalStatisticsHandler(WebRequestHandler):
    def get(self, *args, **kwargs):
        tab = self.request.get('tab', 'info')
        data = {}
        total = TotalStatistics.get()
        if tab == 'info':
            data['words_in_dictionary'] = cache('dict_word', lambda: GlobalDictionaryWord.query().count())
            data['used_words'] = cache('used_words',
                                       lambda: GlobalDictionaryWord.query(GlobalDictionaryWord.used_times > 0).count())
            longest = cache('longest_explanation',
                            lambda: GlobalDictionaryWord.query().order(
                                -GlobalDictionaryWord.total_explanation_time).get())
            if longest:
                data['longest_word'], data['longest_time'] = longest.word, longest.total_explanation_time
            data['total_words'], data['total_games'] = total.words_used, total.games
        elif tab == 'daily':
            data['daily_statistics'] = cache('daily',
                                             lambda: DailyStatistics.query().order(DailyStatistics.date).fetch())
            daily = []
            for el in data['daily_statistics']:
                daily.append((el.games, el.words_used,
                              el.players_participated, el.total_game_duration // 60 * 60,
                              el.date.strftime("%Y-%m-%d")))
            by_hour = [0 for i in range(24)]
            by_day = [0 for i in range(7)]
            for hour, games in enumerate(total.by_hour):
                by_hour[hour % 24] += games
                by_day[(hour // 24 + 3) % 7] += games
            data['daily'] = daily
            data['by_hour'] = by_hour
            data['by_day'] = by_day
            data['by_hour_and_day'] = total.by_hour
        games_for_player_count = cache('for_player_count',
                                       lambda:
                                       GamesForPlayerCount.query().order(GamesForPlayerCount.player_count).fetch())

        self.draw_page("statistics/total_statistic",
                       tab=tab, **data)
