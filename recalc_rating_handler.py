__author__ = 'nikolay'

import json
import trueskill

from all_handler import AllHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from environment import TRUESKILL_ENVIRONMENT


class RecalcRatingHandler(AllHandler):
    def post(self):
        words = json.loads(self.request.get("json"))['words']
        ratings = []
        for word in words:
            word_db = GlobalDictionaryWord.query(GlobalDictionaryWord.word == word).get()
            if word_db is None:
                continue
            ratings.append(TRUESKILL_ENVIRONMENT.create_rating(mu=word_db.E, sigma=word_db.D))
