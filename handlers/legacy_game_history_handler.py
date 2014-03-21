__author__ = 'nikolay'
from google.appengine.ext import ndb
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.api import taskqueue
from collections import defaultdict
import logging
import json


class Word(ndb.Model):
    text = ndb.StringProperty(indexed=False)
    owner = ndb.IntegerProperty(indexed=False)


class WordGuessResult(ndb.Model):
    GUESS, FAIL, PUT_BACK, TIME_OUT = range(4)

    int_repr = {
        u'GUESS': GUESS,
        u'FAIL': FAIL,
        u'PUT_BACK': PUT_BACK,
        u'TIME_OUT': TIME_OUT
    }

    word = ndb.IntegerProperty(indexed=False)
    result = ndb.IntegerProperty(indexed=False)
    time_sec = ndb.FloatProperty(indexed=False)
    round_ = ndb.IntegerProperty(indexed=False)
    """ stores used word info
    word: (ndb.IntegerProperty) index of word
    result: (ndb.IntegerProperty()) guess result, must be in range(4)
    time_sec: (ndb.FloatProperty()) time from beginning of round when\
        word disappeared
    round_: (ndb.IntegerProperty()) id of round in which word was used
    """


class NormalWordGuessResult(object):
    pass


class Round(ndb.Model):
    player_explain = ndb.IntegerProperty(indexed=False)
    player_guess = ndb.IntegerProperty(indexed=False)
    duration_time = ndb.FloatProperty(indexed=False)

    """ stores history of one round
    player_explain: (ndb.StringProperty())
    player_guess: (ndb.StringProperty())
    #words: (ndb.StringProperty(repeated=True)) words used in this round
    """


class GameId(ndb.Model):
    id_ = ndb.IntegerProperty()
    game_local = ndb.BooleanProperty(indexed=False)


class GameHistory(ndb.Model):

    HAT_STANDART, CROCODILE, ONE_WORD = range(3)

    int_repr_type = {
        'HAT_STANDART': HAT_STANDART,
        'CROCODILE': CROCODILE,
        'ONE_WORD': ONE_WORD
    }

    players = ndb.StringProperty(repeated=True, indexed=False)
    rounds = ndb.StructuredProperty(Round, repeated=True, indexed=False)
    guess_results = ndb.StructuredProperty(WordGuessResult,
                                           repeated=True,
                                           indexed=False)
    words = ndb.StructuredProperty(Word, repeated=True, indexed=False)
    unused_words = ndb.StructuredProperty(Word, repeated=True, indexed=False)
    id_ = ndb.StructuredProperty(GameId)
    json_string = ndb.StringProperty(indexed=False)
    pin = ndb.IntegerProperty(indexed=False)
    is_paired = ndb.BooleanProperty(indexed=False)
    game_type = ndb.IntegerProperty(indexed=False)
    game_number = ndb.IntegerProperty(indexed=False)

    """ stores history of a game
    players: (ndb.StringProperty(repeated=True))
    rounds: (ndb.StructuredProperty(Round, repeated=True)) all played rounds
    guess_results: (ndb.StructuredProperty(WordGuessResult, repeated=True))
        results of guessing
    words: (ndb.StructuredProperty(Word, repeated=True))
    """


class LegacyStatisticsHandler(ServiceRequestHandler):

    def post(self):
        game_id = self.request.get('game_id')
        logging.info("Handling legacy history with key {}".format(game_id))
        hist = ndb.Key(GameHistory, int(game_id)).get()
        if hist is None:
            logging.error("Can't find game history")
            self.abort(200)
        if hist.game_type is None:
            hist.game_type = GameHistory.HAT_STANDART
        if hist.game_type != GameHistory.HAT_STANDART:
            logging.info("Do not handle history of non-original-hat game")
            self.abort(200)
        words_by_players_pair = {}
        seen_words_time = defaultdict(lambda: 0)
        word_outcome = {}
        pick_time = 0
        cur_round = 0
        for res in hist.guess_results:
            if res.result in [0, 1]:
                if cur_round != res.round_:
                    pick_time = 0
                r = hist.rounds[res.round_]
                if not res.word in seen_words_time:
                    if not (r.player_explain, r.player_guess) in words_by_players_pair:
                        words_by_players_pair[(r.player_explain, r.player_guess)] = []
                    words_by_players_pair[(r.player_explain, r.player_guess)].append(res)
                    res.time_sec, pick_time = res.time_sec - pick_time, res.time_sec
                    if res.result == 1:
                        res.time_sec = 5 * 60
            seen_words_time[res.word] += int(round(res.time_sec))
            word_outcome[res.word] = res.result
        for i in range(len(hist.words)):
            if i not in seen_words_time:
                continue
            word_db = ndb.Key(GlobalDictionaryWord, hist.words[i].text).get()
            if not word_db:
                continue
            word_db.used_times += 1
            if word_outcome[i] == 0:
                word_db.guessed_times += 1
            elif word_outcome[i] == 1:
                word_db.failed_times += 1
            word_db.total_explanation_time += seen_words_time[i]
            if word_outcome[i] == 0:
                pos = seen_words_time[i] // 5
                l = word_db.counts_by_expl_time
                while pos >= len(l):
                    l.append(0)
                l[pos] += 1
            word_db.put()
        words = [hist.words[w].text for w in sorted(filter(lambda w: word_outcome[w] == 0,
                                                           seen_words_time.keys()),
                                                    key=lambda w: -seen_words_time[w])]
        taskqueue.add(url='/internal/recalc_rating_after_game',
                      params={'json': json.dumps(words)},
                      queue_name='rating_calculation')
        for players_pair, words in words_by_players_pair.items():
            if len(words) > 1:
                words = sorted(words, key=lambda w: -w.time_sec)
                to_recalc = [hist.words[w.word].text for w in words]
                taskqueue.add(url='/internal/recalc_rating_after_game',
                              params={'json': json.dumps(to_recalc)},
                              queue_name='rating_calculation')
