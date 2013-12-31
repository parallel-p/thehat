__author__ = 'nikolay'

import unittest
import webapp2
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed
import json

import main

GAME_JSON = u'''{
    "title": "A game",
    "players": [
        {
            "name": "Vasya",
            "words": [
                {
                    "text": "hat",
                    "origin": "MANUAL_INPUT"
                },
                {
                    "text": "hair",
                    "origin": "RANDOM"
                }
            ]
        }
    ],
    "words": [
        {
            "text": "banana",
            "origin": "PACKAGE"
        },
        {
            "text": "tea",
            "origin": "RANDOM"
        }
    ],
    "settings": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1
    }
}
'''

UPDATE_JSON = u'''{
    "players_add": [
        {
            "name": "Petya",
            "words": [
                {
                    "text": "link",
                    "origin": "MANUAL_INPUT"
                },
                {
                    "text": "dog",
                    "origin": "RANDOM"
                }
            ]
        },
        {
            "name": "Ivan",
            "words": [
                {
                    "text": "bear",
                    "origin": "RANDOM"
                },
                {
                    "text": "coala",
                    "origin": "PERSONAL_DICTIONARY"
                }
            ]
        }
    ],
    "players_del": [
        0
    ],
    "words_add": [
        {
            "text": "apple",
            "origin": "PACKAGE"
        },
        {
            "text": "coffee",
            "origin": "RANDOM"
        }
    ],
    "order": [
        0
    ]
    "settings": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

GAME_JSON_AFTER_UPDATE = u'''{
    "title": "A game",
    "players": [
        {
            "name": "Petya",
            "words": [
                {
                    "text": "link",
                    "origin": "MANUAL_INPUT"
                },
                {
                    "text": "dog",
                    "origin": "RANDOM"
                }
            ]
        },
        {
            "name": "Ivan",
            "words": [
                {
                    "text": "bear",
                    "origin": "RANDOM"
                },
                {
                    "text": "coala",
                    "origin": "PERSONAL_DICTIONARY"
                }
            ]
        }
    ],
    "words": [
        {
            "text": "banana",
            "origin": "PACKAGE"
        },
        {
            "text": "tea",
            "origin": "RANDOM"
        },
        {
            "text": "apple",
            "origin": "PACKAGE"
        },
        {
            "text": "coffee",
            "origin": "RANDOM"
        }
    ],
    "settings": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''


class PreGameHandlersTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def create_game(self):
        post_data = {
            'game': GAME_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/create', None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        return (json_returned['id'], json_returned['pin'])

    def test_create(self):
        self.create_game()
        self.assertEqual(len(PreGame.all()), 1)
        self.assertEqual(PreGame.all()[0].words, ["banana", "tea"])

    def test_get(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/%s' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        was_game = json.loads(GAME_JSON)
        now_game = json.loads(response.body)
        for key in was_game:
            self.assertEqual(was_game[key], now_game[key])
        self.assertEqual(now_game[u'id'], game_id)
        request = webapp2.Request.blank('/other_device_id/pregame/%s' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_update(self):
        game_id, game_pin = self.create_game()
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        need_game = json.loads(GAME_JSON_AFTER_UPDATE)
        now_game = json.loads(response.body)
        for key in need_game:
            self.assertEqual(need_game[key], now_game[key])
        self.assertEqual(now_game[u'id'], game_id)
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id, None, None, post_data)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_version(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        next_version = json.loads(response.body)['version']
        self.assertGreater(next_version, first_version)

    def test_since(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_id/pregame/%s/since/%d' % (game_id, first_version))
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        need_diff = json.loads(UPDATE_JSON)
        now_diff = json.loads(response.body)
        for key in need_diff:
            if key != 'order':
                self.assertEqual(need_diff[key], now_diff[key])

    def test_start(self):
        game_id, game_pin = self.create_game()
        self.assertTrue(PreGame.all()[0].can_join)
        request = webapp2.Request.blank('/device_id/pregame/%s/start' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertFalse(PreGame.all()[0].can_join)
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_abort(self):
        game_id, game_pin = self.create_game()
        self.assertTrue(PreGame.all()[0].can_join)
        request = webapp2.Request.blank('/device_id/pregame/%s/abort' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertFalse(PreGame.all()[0].can_join)
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_join(self):
        game_id, game_pin = self.create_game()
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)
        post_data = {
            'pin': game_pin
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/join' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        post_data = {
            'update': UPDATE_JSON
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()
