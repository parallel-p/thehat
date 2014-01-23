__author__ = 'nikolay'

import json

from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from objects.global_dictionary_word import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT
from objects.game_results_log import GameLog
from base_handlers.service_request_handler import ServiceRequestHandler


class RecalcRatingHandler(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(RecalcRatingHandler, self).__init__(*args, **kwargs)

    def post(self):
        words = json.loads(self.request.get("json"))
        ratings = []
        words_db = []
        for word in words:
            word_db = GlobalDictionaryWord.get_by_key_name(word)
            if word_db is None:
                continue
            words_db.append(word_db)
            ratings.append((TRUESKILL_ENVIRONMENT.create_rating(mu=word_db.E, sigma=word_db.D), ))
        rated = TRUESKILL_ENVIRONMENT.rate(ratings)
        for i in xrange(len(rated)):
            words_db[i].E = rated[i][0].mu
            words_db[i].D = rated[i][0].sigma
            words_db[i].put()
        self.response.write("OK, %d words rated" % len(rated))


MAX_TIME = 5 * 60 * 1000 # 5 minutes
MIN_TIME = 3 * 1000 # 3 seconds


class AddGameHandler(ServiceRequestHandler):
    def post(self):
        game_id = self.request.get('game_id')
        log_db = ndb.Key(GameLog, game_id).get()
        if log_db is None:
            self.response.write('Ooops, no log found')
            self.error(404)
            return
        log = json.loads(log_db.json)
        events = log['events']
        words_orig = log['setup']['words']
        words_seen = []
        words_current = {}
        time_word = {}
        words_by_players_pair = {}
        for event in events:
            if event['type'] == 'round_start':
                for word in words_current.keys():
                    if word not in words_seen:
                        if time_word[word] > MAX_TIME or time_word[word] < MIN_TIME:
                            words_current[word] = 'removed'
                        if words_current[word] == 'guessed':
                            words_by_players_pair[current_pair].append({
                                'word': words_orig[word]['word'],
                                'time': time_word[word]
                            })
                        if words_current[word] == 'failed':
                            words_by_players_pair[current_pair].append({
                                'word': words_orig[word]['word'],
                                'time': MAX_TIME
                            })
                        words_seen.append(word)
                current_pair = (event['from'], event['to'])
                if current_pair not in words_by_players_pair.keys():
                    words_by_players_pair[current_pair] = []
            elif event['type'] == 'stripe_outcome':
                words_current[event['word']] = event['outcome']
                time_word[event['word']] = event['time'] + event['timeExtra']
            elif event['type'] == 'outcome_override':
                words_current[event['word']] = event['outcome']
            # for the last round
        for word in words_current.keys():
            if word not in words_seen:
                if time_word[word] > MAX_TIME or time_word[word] < MIN_TIME:
                    words_current[word] = 'removed'
                if words_current[word] == 'guessed':
                    words_by_players_pair[current_pair].append({
                        'word': words_orig[word]['word'],
                        'time': time_word[word]
                    })
                if words_current[word] == 'failed':
                    words_by_players_pair[current_pair].append({
                        'word': words_orig[word]['word'],
                        'time': MAX_TIME
                    })
                words_seen.append(word)
            # -----------------
        for players_pair in words_by_players_pair.keys():
            words = words_by_players_pair[players_pair]
            if len(words) > 1:
                words = sorted(words, key=lambda w: -w['time'])
                to_recalc = [w['word'] for w in words]
                taskqueue.add(url='/internal/recalc_rating_after_game',
                              params={'json': json.dumps(to_recalc)})