__author__ = 'nikolay'

import unittest
import json

import webapp2
from google.appengine.ext import testbed

import main


GAME_JSON = u'''{
    "title": "A game",
    "players": [
        {
            "id": 0,
            "name": "Vasya",
            "words": [
                "hat",
                "hair"
            ]
        }
    ],
    "words": [
        "banana",
        "tea"
    ],
    "settings": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1
    }
}
'''


class PreGameHandlersTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_create(self):
        post_data = {
            'game': GAME_JSON
        }
        request = webapp2.Request.blank('/abc/pregame/create', None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(len(PreGame.all()), 1)
        self.assertEqual(PreGame.all()[0].words, ["banana", "tea"])

    def test_get(self):
        post_data = {
            'game': GAME_JSON
        }
        request = webapp2.Request.blank('/abc/pregame/create', None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        game_id = json.loads(response.body)[u'id']
        request = webapp2.Request.blank('/abc/pregame/%s' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        was_game = json.loads(GAME_JSON)
        now_game = json.loads(response.body)
        for key in was_game:
            self.assertEqual(was_game[key], now_game[key])
        self.assertEqual(now_game[u'id'], game_id)
        request = webapp2.Request.blank('/abc2/pregame/%s' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()
