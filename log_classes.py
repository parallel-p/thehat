from google.appengine.ext import ndb


class Log(ndb.Model):
    rounds_list = ndb.StructuredProperty(Round, repeated=True)

    def __init__(self, pre_game, rounds_list, **kwargs):
        super(Log).__init__(**kwargs)
        self.game_id = ndb.IntegerProperty()
        #self.pre_game = pre_game
        self.rounds_list = rounds_list

    def add_round(self, round):
        self.rounds_list.append(round)


class Round(ndb.Model):
    guess_player = ndb.StringProperty()
    explain_player = ndb.StringProperty()
    word = ndb.StructuredProperty(Word)

    def __init__(self, guess_player, explain_player, word):
        self.guess_player = guess_player
        self.explain_player = explain_player
        self.word = word


class Word(ndb.Model):
    text = ndb.StringProperty()
    state = ndb.IntegerProperty()
    time_sec = ndb.FloatProperty()
    tries = ndb.IntegerProperty()

    def __init__(self, text, state, time_sec, tries):
        self.text = text
        self.state = state
        self.time_sec = time_sec
        self.tries = tries

