__author__ = 'nikolay'

import json
import unittest

import webapp2
from google.appengine.ext import testbed

from objects.global_dictionary_word import GlobalDictionaryWord
import main


class RecalcRatingTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_game(self):
        game_words = []
        for i in range(5):
            game_words.append(str(i))
            GlobalDictionaryWord(key_name=str(i), word=str(i), E=50.0, D=50.0 / 3).put()
        request = webapp2.Request.blank('/internal/recalc_rating_after_game')
        request.method = 'POST'
        request.body = "json=%s" % json.dumps({"words": game_words})
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body, "OK, 5 words rated")
        last_rating = 100
        for i in range(5):
            word_db = GlobalDictionaryWord.get_by_key_name(str(i))
            self.assertIsNotNone(word_db)
            self.assertGreater(last_rating, word_db.E)
            last_rating = word_db.E

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()

