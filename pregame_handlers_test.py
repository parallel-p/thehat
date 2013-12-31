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
            "id": 1,
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
    },
    "order": [
        1
    ]
}
'''

UPDATE_JSON = u'''{
    "players_add": [
        {
            "id": 2,
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
            "id": 3,
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
        1
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
        3, 2
    ],
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
            "id": 2,
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
            "id": 3,
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
    },
    "order": [
        3, 2
    ]
}
'''

GAME_BIG_JSON = u'''{
    "title": "big game",
    "players": [
        {
            "id": 0,
            "name": "0",
            "words": []
        }
        {
            "id": 1,
            "name": "1",
            "words": []
        }
        {
            "id": 2,
            "name": "2",
            "words": []
        }
        {
            "id": 3,
            "name": "3",
            "words": []
        }
        {
            "id": 4,
            "name": "4",
            "words": []
        }
    ],
    "words": [],
    "order": [0, 1, 2, 3, 4],
    "settings": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

BIG_UPDATE_1 = u'''{
    "players_add": [
        {
            "id": 5,
            "name": "5",
            "words": []
        }
    ],
    "players_del": [
        1
    ],
    "players_upd": [
        {
            "id": 2,
            "name": "2new",
            "words": []
        }
    ]
    "words_add": [],
    "order": none,
    "settings": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

BIG_UPDATE_2 = u'''{
    "players_add": [],
    "players_del": [],
    "words_add": [],
    "order": [4, 2, 0, 1, 3],
    "settings": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

GAME_BIG_AFTER_UPDATE = u'''{
    "title": "big game",
    "players": [
        {
            "id": 0,
            "name": "0",
            "words": []
        }
        {
            "id": 2,
            "name": "2new",
            "words": []
        }
        {
            "id": 3,
            "name": "3",
            "words": []
        }
        {
            "id": 4,
            "name": "4",
            "words": []
        }
        {
            "id": 5,
            "name": "5",
            "words": []
        }
    ],
    "words": [],
    "order": [4, 2, 0, 3, 5],
    "settings": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

TOTAL_UPDATE = u'''{
    "players_add": [
        {
            "id": 5,
            "name": "5",
            "words": []
        }
    ],
    "players_del": [
        1
    ],
    "players_upd": [
        {
            "id": 2,
            "name": "2new",
            "words": []
        }
    ]
    "words_add": [],
    "order": [4, 2, 0, 3, 5],
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

    def test_all_1(self):
        post_data = {
            'game': GAME_BIG_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/create', None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        game_id = json_returned['id']
        game_pin = json_returned['pin']
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        post_data = {
            'update': BIG_UPDATE_1
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        post_data = {
            'pin': game_pin
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/join' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        post_data = {
            'update': BIG_UPDATE_2
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        need_game = json.loads(GAME_BIG_AFTER_UPDATE)
        now_game = json.loads(response.body)
        for key in need_game:
            self.assertEqual(need_game[key], now_game[key])
        request = webapp2.Request.blank('/other_device_id/pregame/%s/since/%d' % (game_id, first_version))
        response = request.get_response(main.app)
        need_diff = json.loads(TOTAL_UPDATE)
        now_diff = json.loads(response.body)
        for key in need_game:
            self.assertEqual(need_diff[key], now_diff[key])


    def test_all_2(self):
        post_data = {
            'game': GAME_BIG_JSON
        }
        request = webapp2.Request.blank('/device_id/pregame/create', None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        game_id = json_returned['id']
        game_pin = json_returned['pin']
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        post_data = {
            'update': BIG_UPDATE_2
        }
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        post_data = {
            'pin': game_pin
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/join' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        post_data = {
            'update': BIG_UPDATE_1
        }
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id, None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        need_game = json.loads(GAME_BIG_AFTER_UPDATE)
        now_game = json.loads(response.body)
        for key in need_game:
            self.assertEqual(need_game[key], now_game[key])
        request = webapp2.Request.blank('/other_device_id/pregame/%s/since/%d' % (game_id, first_version))
        response = request.get_response(main.app)
        need_diff = json.loads(TOTAL_UPDATE)
        now_diff = json.loads(response.body)
        for key in need_game:
            self.assertEqual(need_diff[key], now_diff[key])


    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()
