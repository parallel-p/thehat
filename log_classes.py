from google.appengine.ext import ndb


class Log(ndb.Model):
    game_id = None

    def __init__(self, pre_game, rounds_list):
        self.game_id = ndb.IntegerProperty()
        self.rounds_list = ndb.StructuredProperty(Round, repeated=True)
        self.pre_game = pre_game
        self.rounds_list = rounds_list
        self.game_id = game_id

    def add_round(self, round):
        self.rounds_list.append(round)


class Round(ndb.Model):
    def __init__(self, guess_player, explain_player, word):
        self.guess_player = ndb.StringProperty()
        self.explain_player = ndb.StringProperty()
        self.word = ndb.StructuredProperty(Word)
        self.guess_player = guess_player
        self.explain_player = explain_player
        self.word = word


class Word(ndb.Model):
    def __init__(self, text, state, time_sec, tries):
        self.text = ndb.StringProperty()
        self.state = ndb.IntegerProperty()
        self.time_sec = ndb.FloatProperty()
        self.tries = ndb.IntegerProperty()
        self.text = text
        self.state = state
        self.time_sec = time_sec
        self.tries = tries

