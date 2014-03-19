__author__ = 'nikolay'

import json
import logging
from collections import defaultdict

from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from objects.global_dictionary_word import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT
from objects.game_results_log import GameLog
from legacy_game_history_handler import GameHistory
from base_handlers.service_request_handler import ServiceRequestHandler


class BadGameError(Exception):
    pass


class RecalcRatingHandler(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(RecalcRatingHandler, self).__init__(*args, **kwargs)

    def post(self):
        words = json.loads(self.request.get("json"))
        ratings = []
        words_db = []
        for word in words:
            word_db = ndb.Key(GlobalDictionaryWord, word).get()
            if word_db is None:
                logging.warning(u"There is no word '{}' in our dictionary".format(word))
                continue
            words_db.append(word_db)
            ratings.append((TRUESKILL_ENVIRONMENT.create_rating(mu=word_db.E, sigma=word_db.D), ))
        if len(ratings) > 1:
            rated = TRUESKILL_ENVIRONMENT.rate(ratings)
            for i in xrange(len(rated)):
                words_db[i].E = rated[i][0].mu
                words_db[i].D = rated[i][0].sigma
                words_db[i].put()
            logging.info(u"Updated rating of words: {}".format(", ".join([el.word for el in words_db])))
        else:
            logging.warning("No word from pair is in our dictionary")
        self.response.set_status(200)


MAX_TIME = 5 * 60 * 1000  # 5 minutes
MIN_TIME = 500  # 0.5 second


class AddGameHandler(ServiceRequestHandler):
    def post(self):
        game_id = self.request.get('game_id')
        logging.info("Handling log of game {}".format(game_id))
        log_db = ndb.Key(GameLog, game_id).get()
        if log_db is None:
            self.abort(404)
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
            i = 0
            while i < len(events) and events[i]['type'] != 'round_start':
                if events[i]['type'] != 'start_game':
                    logging.warning("Unexpected {} event before the first round start".format(events[i]['type']))
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
                if i not in seen_words_time:
                    continue
                word_db = ndb.Key(GlobalDictionaryWord, words_orig[i]['word']).get()
                if not word_db:
                    continue
                word_db.used_times += 1
                if words_outcome[i] == 'guessed':
                    word_db.guessed_times += 1
                elif words_outcome[i] == 'failed':
                    word_db.failed_times += 1
                word_db.total_explanation_time += seen_words_time[i] // 1000
                pos = seen_words_time[i] // 5000
                l = word_db.counts_by_expl_time
                while pos >= len(l):
                    l.append(0)
                l[pos] += 1
                word_db.put()
            words = [words_orig[w]['word'] for w in sorted(filter(lambda w: words_outcome[w] == 'guessed',
                                                          seen_words_time.keys()),
                                                   key=lambda w: -seen_words_time[w])]
            taskqueue.add(url='/internal/recalc_rating_after_game',
                          params={'json': json.dumps(words)})
            for players_pair, words in words_by_players_pair.items():
                if len(words) > 1:
                    words = sorted(words, key=lambda w: -w['time'])
                    to_recalc = [w['word'] for w in words]
                    taskqueue.add(url='/internal/recalc_rating_after_game',
                                  params={'json': json.dumps(to_recalc)})
        except BadGameError:
            self.abort(200)


class RecalcAllLogs(ServiceRequestHandler):
    def post(self):
        logs = GameLog.query().fetch(keys_only=True)
        for el in logs:
            taskqueue.add(url='/internal/add_game_to_statistic', params={'game_id': el.id()}, countdown=5)
        hist = GameHistory.query().fetch(keys_only=True)
        for el in hist:
            taskqueue.add(url='/internal/add_legacy_game', params={'game_id': el.id()})