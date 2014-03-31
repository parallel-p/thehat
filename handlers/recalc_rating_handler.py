__author__ = 'nikolay'

import json
import logging
from collections import defaultdict

from google.appengine.api import taskqueue

from objects.global_dictionary_word import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT
from objects.game_results_log import GameLog
from legacy_game_history_handler import GameHistory
from base_handlers.service_request_handler import ServiceRequestHandler
from base_handlers.admin_request_handler import AdminRequestHandler
from random import randint
from objects.total_statistics_object import *
import datetime


class BadGameError(Exception):
    pass


class RecalcRatingHandler(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(RecalcRatingHandler, self).__init__(*args, **kwargs)

    @ndb.transactional_tasklet()
    def update_word(self, word, E, D):
        word_db = yield ndb.Key(GlobalDictionaryWord, word).get_async()
        word_db.E = E
        word_db.D = D
        yield word_db.put_async()

    @ndb.toplevel
    def post(self):
        words = [ndb.Key(GlobalDictionaryWord, word) for word in json.loads(self.request.get("json"))]
        ratings = []
        words = ndb.get_multi(words)
        words_db = []
        for word_db in words:
            if word_db is None:
                continue
            words_db.append(word_db)
            ratings.append((TRUESKILL_ENVIRONMENT.create_rating(mu=word_db.E, sigma=word_db.D), ))
        if len(ratings) > 1:
            rated = TRUESKILL_ENVIRONMENT.rate(ratings)
            for i in xrange(len(rated)):
                self.update_word(words_db[i].word, rated[i][0].mu, rated[i][0].sigma)
            logging.info(u"Updated rating of {} word".format(len(ratings)))
        else:
            logging.warning("No word from pair is in our dictionary")
        self.response.set_status(200)


MAX_TIME = 5 * 60 * 1000  # 5 minutes
MIN_TIME = 500  # 0.5 second


def get_date(time):
    return time - time % (60 * 60 * 24)


class AddGameHandler(ServiceRequestHandler):

    @ndb.transactional_tasklet()
    def update_daily_statistics(self, game_date, word_count, players_count, duration):
        statistics = ((yield ndb.Key(DailyStatistics, str(game_date)).get_async()) or
                      DailyStatistics(date=datetime.datetime.fromtimestamp(game_date),
                                      id=str(game_date)))
        statistics.words_used += word_count
        statistics.players_participated += players_count
        statistics.games += 1
        statistics.total_game_duration += duration
        yield statistics.put_async()

    @ndb.transactional_tasklet()
    def update_statistics_by_player_count(self, player_count):
        statistics = ((yield ndb.Key(GamesForPlayerCount, str(player_count)).get_async()) or
                      GamesForPlayerCount(player_count=player_count,
                                          id=str(player_count)))
        statistics.games += 1
        statistics.put()

    @ndb.transactional_tasklet()
    def update_statistics_by_hour(self, game_time):
        hour = (game_time % (60 * 60 * 24) // (60 * 60))
        statistics = ((yield ndb.Key(GamesForHour, str(hour)).get_async()) or
                      GamesForHour(hour=hour, id=str(hour)))
        statistics.games += 1
        yield statistics.put_async()

    @ndb.transactional_tasklet()
    def update_word(self, word, word_outcome, explanation_time, game_id):
        word_db = yield ndb.Key(GlobalDictionaryWord, word).get_async()
        if not word_db:
            return
        word_db.used_times += 1
        if word_outcome == 'guessed':
            word_db.guessed_times += 1
        elif word_outcome == 'failed':
            word_db.failed_times += 1
        time_sec = int(round(explanation_time / 1000.0))
        word_db.total_explanation_time += time_sec
        if word_outcome == 'guessed':
            pos = time_sec // 5
            l = word_db.counts_by_expl_time
            while pos >= len(l):
                l.append(0)
            l[pos] += 1
        word_db.used_games.append(game_id)
        word_db.danger = word_db.failed_times / word_db.used_times
        yield word_db.put_async()

    @ndb.toplevel
    def post(self):
        game_id = self.request.get('game_id')
        logging.info("Handling log of game {}".format(game_id))
        log_db = ndb.Key(GameLog, game_id).get()
        if log_db is None:
            logging.error("Can't find game log")
            self.abort(200)
        try:
            log = json.loads(log_db.json)

            #TODO: solve problem with free-play games
            if log['setup']['type'] == "freeplay":
                raise BadGameError()
            events = log['events']
            words_orig = log['setup']['words']
            seen_words_time = defaultdict(lambda: 0)
            words_outcome = {}
            current_words_time = {}
            words_by_players_pair = {}

            start_timestamp = None
            finish_timestamp = None
            for i in events:
                if i["type"] == "end_game":
                    finish_timestamp = i["time"]
            i = 0
            while i < len(events) and events[i]['type'] != 'round_start':
                if events[i]['type'] != 'start_game':
                    logging.warning("Unexpected {} event before the first round start".format(events[i]['type']))
                else:
                    start_timestamp = events[i]["time"]
                i += 1
            while i < len(events):
                current_pair = (events[i]['from'], events[i]['to'])
                if current_pair not in words_by_players_pair:
                    words_by_players_pair[current_pair] = []
                i += 1
                while i < len(events) and events[i]['type'] != 'round_start':
                    event = events[i]
                    if event['type'] == 'stripe_outcome':
                        words_outcome[event['word']] = event['outcome']
                        current_words_time[event['word']] = event['time'] + event['timeExtra']
                    elif event['type'] == 'outcome_override':
                        if not event['word'] in words_outcome:
                            raise BadGameError()
                        words_outcome[event['word']] = event['outcome']
                    else:
                        if event['type'] not in ('finish_round', 'end_game', 'pick_stripe'):
                            logging.warning("Event of unknown type {}".format(event['type']))
                    i += 1
                for word in current_words_time.keys():
                    if current_words_time[word] > MAX_TIME or current_words_time[word] < MIN_TIME:
                        words_outcome[word] = 'removed'
                    elif words_outcome[word] in ('guessed', 'failed'):
                        if not word in seen_words_time:
                            words_by_players_pair[current_pair].append({
                                'word': words_orig[word]['word'],
                                'time': current_words_time[word] if words_outcome[word] == 'guessed' else MAX_TIME
                            })
                    seen_words_time[word] += current_words_time[word]
                current_words_time.clear()

            for i in range(len(words_orig)):
                if i in seen_words_time:
                    self.update_word(words_orig[i]['word'], words_outcome[i], seen_words_time[i], game_id)

            words = [words_orig[w]['word'] for w in sorted(filter(lambda w: words_outcome[w] == 'guessed',
                                                                  seen_words_time.keys()),
                                                           key=lambda w: -seen_words_time[w])]
            taskqueue.add(url='/internal/recalc_rating_after_game',
                          params={'json': json.dumps(words)},
                          queue_name='rating-calculation')
            for players_pair, words in words_by_players_pair.items():
                if len(words) > 1:
                    words = sorted(words, key=lambda w: -w['time'])
                    to_recalc = [w['word'] for w in words]
                    taskqueue.add(url='/internal/recalc_rating_after_game',
                                  params={'json': json.dumps(to_recalc)},
                                  queue_name='rating-calculation')

            players_count = len(log["setup"]["players"]) if "players" in log["setup"] else 0
            if start_timestamp:
                start_timestamp //= 1000
                if finish_timestamp:
                    finish_timestamp //= 1000
                    duration = finish_timestamp - start_timestamp
                else:
                    duration = 0
                game_date = get_date(start_timestamp)
                self.update_daily_statistics(game_date, len(seen_words_time), players_count, duration)
                self.update_statistics_by_hour(start_timestamp)
            if players_count:
                self.update_statistics_by_player_count(players_count)

        except (BadGameError, KeyError):
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
        word.used_legacy_games = []
        yield word.put_async()

    @staticmethod
    def delete_all_stat():
        for t in [DailyStatistics, GamesForHour, GamesForPlayerCount]:
            ndb.delete_multi(t.query().fetch(keys_only=True))

    def next_stage(self):
        if self.stage == 4:
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
            map(lambda k: queue.add_async(taskqueue.Task(url='/internal/add_game_to_statistic',
                                                         params={'game_id': k.id()})),
                self.fetch_portion(GameLog.query(), keys_only=True))
        elif self.stage == 4:
            map(lambda k: queue.add_async(taskqueue.Task(url='/internal/add_legacy_game',
                                          params={'game_id': k.id()})),
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
            '/internal/update_heatmap/task_queue',
            '/internal/update_heatmap/task_queue',
            '/internal/update_scatter/task_queue',
            '/internal/update_scatter/task_queue',
            '/internal/update_scatter/task_queue']
    params = [{}, {'stage': 'hash'}, {'stage': 'mark'}, {'stage': 'remove'},
                  {'N': '1'}, {'N': '2'}, {'N': '1'}, {'N': '2'}, {'N': '3'}]

    def post(self):
        code = self.request.get('code')
        action = int(self.request.get('action'))
        message = 0
        if code:
            if code == self.request.get('ans'):
                taskqueue.add(url=self.urls[action-1], params=self.params[action-1])
                message = 1
            else:
                message = 2
        a = randint(10, 99)
        b = randint(10, 99)
        self.draw_page('logs_administration', message=message, a=a, b=b)

    def get(self):
        a = randint(10, 99)
        b = randint(10, 99)
        self.draw_page('logs_administration', message=0, a=a, b=b)