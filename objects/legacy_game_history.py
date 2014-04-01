__author__ = 'nikolay'
from google.appengine.ext import ndb


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
    string_repr = ['guessed', 'failed', 'put_back', 'timed_out']

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
    hash = ndb.StringProperty()
    ignored = ndb.BooleanProperty(default=False)

    """ stores history of a game
    players: (ndb.StringProperty(repeated=True))
    rounds: (ndb.StructuredProperty(Round, repeated=True)) all played rounds
    guess_results: (ndb.StructuredProperty(WordGuessResult, repeated=True))
        results of guessing
    words: (ndb.StructuredProperty(Word, repeated=True))
    """
