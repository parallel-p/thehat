__author__ = 'nikolay'

import json

from all_handler import AllHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT


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