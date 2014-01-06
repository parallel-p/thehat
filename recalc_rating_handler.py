__author__ = 'nikolay'

import json

from google.appengine.api import taskqueue

from all_handler import AllHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT
from objects.game_results_log import GameLog


class RecalcRatingHandler(AllHandler):
    def post(self):
        words = json.loads(self.request.get("json"))['words']
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


class AddGameHandler(AllHandler):
    def post(self):
        game_id = self.request.get('game_id')
        log = GameLog.query(GameLog.game_id == game_id).get()
        print game_id
        if log is None:
            print "oooops, no log found"
            return
        events = json.loads(log)['events']
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
                            words_by_players_pair[current_pair].append({'word': word, 'time': time_word[word]})
                        if words_current[word] == 'failed':
                            words_by_players_pair[current_pair].append({'word': word, 'time': MAX_TIME})
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
                    words_by_players_pair[current_pair].append({'word': word, 'time': time_word[word]})
                if words_current[word] == 'failed':
                    words_by_players_pair[current_pair].append({'word': word, 'time': MAX_TIME})
                words_seen.append(word)
        # -----------------
        for players_pair in words_by_players_pair.keys():
            words = words_by_players_pair[players_pair]
            print words
            if len(words) > 1:
                words = sorted(words, key=lambda w: w['time'])
                to_recalc = [w['word'] for w in words]
                taskqueue.add(url='/internal/recalc_statistic_after_game',
                              params={'json': json.dumps(to_recalc)})