# -*- coding: utf-8 -*-
from handlers import AdminRequestHandler, ServiceRequestHandler

__author__ = 'nikolay'


import json
import logging
from collections import defaultdict
from random import randint
import datetime

from google.appengine.api import taskqueue
from google.appengine.api import memcache

from objects.global_dictionary import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT
from objects.game_results_log import GameLog
from objects.legacy_game_history import GameHistory
from objects.total_statistics_object import *
from objects.unknown_word import UnknownWord
from handlers.statistics.game_len_prediction import GameLength


class BadGameError(Exception):
    def __init__(self, reason):
        self.reason = reason


MAX_TIME = 5 * 60 * 1000  # 5 minutes
MIN_TIME = 500  # 0.5 second
DEFAULT_OFFSET = 4*60*60*1000


def get_date(time):
    return time - time % (60 * 60 * 24)


class AddGameHandler(ServiceRequestHandler):
    ratings = []

    @staticmethod
    def check_word(word):
        if GlobalDictionaryWord.get(word) is None:
            on_server = ndb.Key(UnknownWord, word).get()
            if on_server is None:
                UnknownWord(word=word, id=word, times_used=1).put()
            elif not on_server.ignored:
                on_server.times_used += 1
                on_server.put()

    @ndb.transactional()
    def update_daily_statistics(self, game_date, word_count, players_count, duration):
        statistics = (ndb.Key(DailyStatistics, str(game_date)).get() or
                      DailyStatistics(date=datetime.datetime.fromtimestamp(game_date),
                                      id=str(game_date)))
        statistics.words_used += word_count
        statistics.players_participated += players_count
        statistics.games += 1
        statistics.total_game_duration += duration
        statistics.put()

    @ndb.transactional()
    def update_statistics_by_player_count(self, player_count):
        statistics = (ndb.Key(GamesForPlayerCount, str(player_count)).get() or
                      GamesForPlayerCount(player_count=player_count,
                                          id=str(player_count)))
        statistics.games += 1
        statistics.put()

    @ndb.transactional()
    def update_total_statistics(self, word_count, game_time=None):
        statistics = TotalStatistics.get()
        statistics.games += 1
        statistics.words_used += word_count
        if game_time:
            hour = game_time / (60 * 60) % (24 * 7)
            statistics.by_hour[hour] += 1
        statistics.put()

    @ndb.transactional(xg=True)
    def update_word(self, word, word_outcome, explanation_time, rating, game_key):
        word_db = GlobalDictionaryWord.get(word)
        if not word_db:
            return
        word_db.used_times += 1
        if word_outcome == 'guessed':
            word_db.guessed_times += 1
        elif word_outcome == 'failed':
            word_db.failed_times += 1
        time_sec = explanation_time
        word_db.total_explanation_time += time_sec
        if word_outcome == 'guessed':
            pos = time_sec // 5
            l = word_db.counts_by_expl_time
            while pos >= len(l):
                l.append(0)
            l[pos] += 1
        word_db.used_games.append(game_key.urlsafe())
        word_db.E = rating.mu
        word_db.D = rating.sigma
        word_db.put()

    def update_game_len_prediction(self, player_count, game_type, game_len):
        key = "{0}_{1}".format(game_type, player_count)
        prediction_db = ndb.Key(GameLength, key).get()
        if prediction_db is None:
            GameLength(lens=[game_len], player_count=player_count, type=game_type, id=key).put()
        else:
            prediction_db.lens.append(game_len)
            prediction_db.put()

    def rate(self, words, coef=None):
        ratings = [{word: self.ratings[word]} for word in words if self.ratings[word]]
        if len(ratings) > 1:
            rated = TRUESKILL_ENVIRONMENT.rate(ratings, partial_update=coef)
            for d in rated:
                word, rate = d.items()[0]
                self.ratings[word] = rate

    def parse_log(self, log_db):
        log = json.loads(log_db.json)
        #TODO: solve problem with free-play games
        if log['setup']['type'] == "freeplay":
            raise BadGameError('old_version')
        events = log['events']
        words_orig = [el['word'] for el in log['setup']['words']]
        explained_at_once = [False]*len(words_orig)
        seen_by_player = defaultdict(lambda: set())
        seen_words_time = defaultdict(lambda: 0)
        words_outcome = {}
        explained_pair = {}
        current_words_time = {}
        start_timestamp = None
        finish_timestamp = None

        for i in events:
            if i["type"] == "end_game":
                finish_timestamp = i["time"]
                if 'aborted' in i and i['aborted']:
                    log_db.reason = 'aborted'
                    log_db.put()
        i = 0
        while i < len(events) and events[i]['type'] != 'round_start':
            if events[i]['type'] != 'start_game':
                logging.warning("Unexpected {} event before the first round start".format(events[i]['type']))
            else:
                start_timestamp = events[i]["time"]
            i += 1
        while i < len(events):
            current_pair = (events[i]['from'], events[i]['to'])
            i += 1
            while i < len(events) and events[i]['type'] != 'round_start':
                event = events[i]
                if event['type'] == 'stripe_outcome':
                    words_outcome[event['word']] = event['outcome']
                    current_words_time[event['word']] = event['time'] + event['timeExtra']
                elif event['type'] == 'outcome_override':
                    if not event['word'] in words_outcome:
                        raise BadGameError("format-error")
                    words_outcome[event['word']] = event['outcome']
                else:
                    if event['type'] not in ('finish_round', 'end_game', 'pick_stripe'):
                        logging.warning("Event of unknown type {}".format(event['type']))
                i += 1
            for word in current_words_time.keys():
                if word in seen_by_player[current_pair[0]]:
                    seen_words_time.pop(word, None)
                    continue
                if current_words_time[word] > MAX_TIME or current_words_time[word] < MIN_TIME:
                    words_outcome[word] = 'removed'
                elif words_outcome[word] in ('guessed', 'failed'):
                    if not word in seen_words_time:
                        explained_at_once[word] = True
                    explained_pair[word] = current_pair
                seen_words_time[word] += int(round(current_words_time[word] / 1000.0))
                seen_by_player[current_pair[0]].add(word)
            current_words_time.clear()
        player_count = len(log["setup"]["players"]) if "players" in log["setup"] else 0
        try:
            offset = int(log['setup']['meta']['time.offset'])
        except KeyError:
            offset = DEFAULT_OFFSET
        if start_timestamp:
            start_timestamp += offset
        if finish_timestamp:
            finish_timestamp += offset
        return (words_orig, seen_words_time, words_outcome, explained_at_once, explained_pair, player_count,
                start_timestamp, finish_timestamp)

    def parse_history(self, hist):
        if hist.game_type is None:
            hist.game_type = GameHistory.HAT_STANDART
        if hist.game_type != GameHistory.HAT_STANDART:
            raise BadGameError('not_hat')
        words_orig = [el.text for el in hist.words]
        explained_at_once = [False]*len(words_orig)
        explained_pair = {}
        seen_by_player = defaultdict(lambda: set())
        seen_words_time = defaultdict(lambda: 0)
        words_outcome = {}
        pick_time = 0
        cur_round = 0
        for res in hist.guess_results:
            if cur_round != res.round_:
                pick_time = 0
                cur_round = res.round_
            res.time_sec -= pick_time
            pick_time += res.time_sec
            r = hist.rounds[cur_round]
            if res.result in [0, 1]:
                explained_pair[res.word] = (r.player_explain, r.player_guess)
                if not res.word in seen_words_time:
                    explained_at_once[res.word] = True
            if res.word in seen_by_player[r.player_explain]:
                seen_words_time.pop(res.word, None)
                continue
            seen_words_time[res.word] += int(round(res.time_sec))
            words_outcome[res.word] = hist.string_repr[res.result]
            seen_by_player[r.player_explain].add(res.word)
        player_count = len(hist.players)
        return words_orig, seen_words_time, words_outcome, explained_at_once, explained_pair, player_count, None, None

    @ndb.toplevel
    def post(self):
        game_key = ndb.Key(urlsafe=self.request.get('game_key'))
        logging.info("Handling log of game {}".format(game_key.id()))
        if game_key.kind() not in ('GameLog', 'GameHistory'):
            self.abort(200)
        log_db = game_key.get()
        if log_db is None:
            logging.error("Can't find game log")
            self.abort(200)
        is_legacy = game_key.kind() == 'GameHistory'
        try:
            words_orig, seen_words_time, words_outcome, explained_at_once, explained_pair, players_count,\
                start_timestamp, finish_timestamp = self.parse_history(log_db) if is_legacy else self.parse_log(log_db)
            if start_timestamp and finish_timestamp:
                self.update_game_len_prediction(players_count, 'game', finish_timestamp - start_timestamp)
            bad_words_count = 0
            for k, v in seen_words_time.items():
                if v < 2:
                    bad_words_count += 1
            if 2*len(seen_words_time) < len(words_orig):
                raise BadGameError('suspect_too_little_words')
            if 2*bad_words_count > len(seen_words_time):
                raise BadGameError('suspect_too_quick_explanation')

            for word in words_orig:
                self.check_word(word)

            word_db = [GlobalDictionaryWord.get(word) for word in words_orig]
            self.ratings = [TRUESKILL_ENVIRONMENT.create_rating(word.E, word.D) if word else None for word in word_db]

            d = defaultdict(list)
            for word in seen_words_time:
                if explained_at_once[word]:
                    d[explained_pair[word]].append(word)
            for l in d.values():
                l.sort(key=lambda item: (words_outcome[item] != 'failed', -seen_words_time[item]))
                self.rate(l)

            d.clear()
            d = defaultdict(list)
            for word in seen_words_time:
                if words_outcome[word] in ('guessed', 'failed'):
                    d[explained_pair[word][0]].append(word)
            for l in d.values():
                l.sort(key=lambda item: (words_outcome[item] != 'failed', -seen_words_time[item]))
                self.rate(l, coef=0.3)

            d.clear()
            for word in seen_words_time:
                if words_outcome[word] == 'guessed':
                    d[explained_pair[word][1]].append(word)
            for l in d.values():
                l.sort(key=lambda item: -seen_words_time[item])
                self.rate(l, coef=0.8)

            words = []
            for word in seen_words_time:
                if words_outcome[word] in ('guessed', 'failed'):
                    words.append(word)
            words.sort(key=lambda item: (words_outcome[item] != 'failed', -seen_words_time[item]))
            self.rate(words, coef=0.6)
            for i in range(len(words_orig)):
                if i in seen_words_time:
                    self.update_word(words_orig[i], words_outcome[i], seen_words_time[i], self.ratings[i], game_key)

            if start_timestamp:
                start_timestamp //= 1000
                if finish_timestamp:
                    finish_timestamp //= 1000
                    duration = finish_timestamp - start_timestamp
                else:
                    duration = 0
                game_date = get_date(start_timestamp)
                self.update_daily_statistics(game_date, len(seen_words_time), players_count, duration)
            self.update_total_statistics(len(seen_words_time), start_timestamp)
            if players_count:
                self.update_statistics_by_player_count(players_count)
            memcache.delete_multi(["danger_top", "words_top", "words_bottom", "used_words_count"])
        except BadGameError as e:
            if isinstance(e, BadGameError):
                reason = e.reason
            else:
                reason = 'format-error'
            log_db.ignored = True
            log_db.reason = reason
            log_db.put()
            logging.warning("Did not handle and marked this game as ignored: {}".format(log_db.reason))
            self.abort(200)


class RecalcAllLogs(ServiceRequestHandler):
    stage = 1
    start_cursor = ndb.Cursor
    cursor = ndb.Cursor()
    more = False

    @ndb.tasklet
    def reset_word(self, word):
        word.E = 50.0
        word.D = 50.0 / 3
        word.used_times = 0
        word.guessed_times = 0
        word.failed_times = 0
        word.total_explanation_time = 0
        word.counts_by_expl_time = []
        word.used_games = []
        yield word.put_async()

    @staticmethod
    def delete_all_stat():
        TotalStatistics(id="total_statistics").put()
        for t in ['DailyStatistics', 'GamesForHour', 'GamesForPlayerCount', 'UnknownWord']:
            ndb.delete_multi(ndb.Query(kind=t).fetch(keys_only=True))

    def next_stage(self):
        if self.stage == 5:
            return
        taskqueue.add(url="/internal/recalc_all_logs",
                      params={"stage": str(self.stage+1)},
                      queue_name="statistic-calculation")

    def next_portion(self):
        taskqueue.add(url="/internal/recalc_all_logs",
                      params={"stage": str(self.stage), "cursor": self.cursor.urlsafe()},
                      queue_name="statistic-calculation")

    def fetch_portion(self, query, **kwargs):
        portion, self.cursor, self.more = query.fetch_page(100, start_cursor=self.start_cursor, **kwargs)
        return portion

    def post(self):
        self.stage = int(self.request.get('stage', 1))
        self.start_cursor = ndb.Cursor(urlsafe=self.request.get('cursor'))
        queue = taskqueue.Queue('logs-processing')
        if self.stage == 1:
            RecalcAllLogs.delete_all_stat()
            self.next_stage()
            self.abort(200)
        elif self.stage == 2:
            words = self.fetch_portion(GlobalDictionaryWord.query(GlobalDictionaryWord.used_times > 0))
            for fut in map(self.reset_word, words):
                fut.get_result()
        elif self.stage == 3:
            logs = self.fetch_portion(GameLog.query())
            for el in logs:
                if not el.ignored:
                    el.ignored = False
                    el.put()
        elif self.stage == 4:
            map(lambda k: queue.add_async(taskqueue.Task(url='/internal/add_game_to_statistic',
                                                         params={'game_key': k.urlsafe()})),
                self.fetch_portion(GameLog.query(GameLog.ignored == False), keys_only=True))
        elif self.stage == 5:
            map(lambda k: queue.add_async(taskqueue.Task(url='/internal/add_game_to_statistic',
                                          params={'game_key': k.urlsafe()})),
                self.fetch_portion(GameHistory.query(GameHistory.ignored == False), keys_only=True))
        if self.more and self.cursor:
            self.next_portion()
        else:
            self.next_stage()


class LogsAdminPage(AdminRequestHandler):
    urls = ['/internal/recalc_all_logs',
            '/remove_duplicates',
            '/remove_duplicates',
            '/remove_duplicates',
            "/cron/update_plots/start/admin"]
    params = [{}, {'stage': 'hash'}, {'stage': 'mark'}, {'stage': 'remove'}, {}]
    task_name = [u'Пересчитать статистику',
                 u"Посчитать хэши старых игр",
                 u"Пометить дубликаты старых игр",
                 u"Удалить дубликаты старых игр",
                 u"Обновить все графики"]

    def post(self):
        code = self.request.get('code')
        action = int(self.request.get('action'))
        message = 0
        if code:
            if code == self.request.get('ans'):
                if action == 5:
                    self.redirect(self.urls[action-1])
                else:
                    taskqueue.add(url=self.urls[action-1], params=self.params[action-1])
                    message = 1
            else:
                message = 2
        a = randint(10, 99)
        b = randint(10, 99)
        self.draw_page('logs_administration', message=message, a=a, b=b, names=self.task_name,
                       last_value=int(action))

    def get(self):
        a = randint(10, 99)
        b = randint(10, 99)
        self.draw_page('logs_administration', message=0, a=a, b=b, names=self.task_name)