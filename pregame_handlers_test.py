__author__ = 'nikolay'

import unittest

import webapp2
from google.appengine.ext import testbed

import main
from objects.pregame import *


GAME_JSON = '''{
    "title": "A game",
    "version": 5,
    "players": [
        {
            "id": "1",
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
    "meta": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1
    },
    "order": [
        "1"
    ]
}
'''

GAME_ON_SERVER_JSON = '''{
    "title": "A game",
    "version": 5,
    "players": [
        {
            "id": "1",
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
            ],
            "last_update": 5
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
    "words_last_update": 5,
    "order_last_update": 5,
    "meta": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1,
        "last_update": 5
    },
    "order": [
        "1"
    ]
}
'''

JSON_JOIN = '''{
    "key": 0,
    "game": {
        "pin": 0,
        "title": "A game",
        "version": 5,
        "players": [
            {
                "id": "1",
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
        "meta": {
            "time_per_round": 20,
            "words_per_player": 10,
            "skip_count": 1
        },
        "order": [
            "1"
        ]
    }
}
'''

UPDATE_JSON = '''{
    "updated_players": [
        {
            "id": "2",
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
            "id": "3",
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
    "players_delete": [
        "1"
    ],
    "updated_words": [
        {
            "text": "apple",
            "origin": "PACKAGE"
        },
        {
            "text": "coffee",
            "origin": "RANDOM"
        }
    ],
    "updated_order": [
        "3", "2"
    ],
    "updated_meta": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

SINCE_JSON = '''{
    "version": 6,
    "updated_players": [
        {
            "id": "2",
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
            "id": "3",
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
    "players_delete": [
        "1"
    ],
    "updated_words": [
        {
            "text": "apple",
            "origin": "PACKAGE"
        },
        {
            "text": "coffee",
            "origin": "RANDOM"
        }
    ],
    "updated_order": [
        "3", "2"
    ],
    "updated_meta": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

GAME_JSON_AFTER_UPDATE = '''{
    "title": "A game",
    "version": 6,
    "players": [
        {
            "id": "2",
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
            "id": "3",
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
            "text": "apple",
            "origin": "PACKAGE"
        },
        {
            "text": "coffee",
            "origin": "RANDOM"
        }
    ],
    "meta": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    },
    "order": [
        "3", "2"
    ]
}
'''

GAME_BIG_JSON = '''{
    "title": "big game",
    "players": [
        {
            "id": "0",
            "name": "0",
            "words": []
        },
        {
            "id": "1",
            "name": "1",
            "words": []
        },
        {
            "id": "2",
            "name": "2",
            "words": []
        },
        {
            "id": "3",
            "name": "3",
            "words": []
        },
        {
            "id": "4",
            "name": "4",
            "words": []
        }
    ],
    "words": [],
    "order": ["0", "1", "2", "3", "4"],
    "meta": {
        "time_per_round": 20,
        "words_per_player": 100,
        "skip_count": 0
    }
}
'''

BIG_UPDATE_1 = '''{
    "updated_players": [
        {
            "id": "2",
            "name": "2new",
            "words": []
        },
        {
            "id": "3",
            "name": "3new",
            "words": []
        }
    ]
}
'''

BIG_UPDATE_2 = '''{
    "updated_order": ["4", "2", "0", "1", "3"],
    "updated_meta": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

GAME_BIG_AFTER_UPDATE = '''{
    "title": "big game",
    "version": 2,
    "players": [
        {
            "id": "0",
            "name": "0",
            "words": []
        },
        {
            "id": "1",
            "name": "1",
            "words": []
        },
        {
            "id": "2",
            "name": "2new",
            "words": []
        },
        {
            "id": "3",
            "name": "3new",
            "words": []
        },
        {
            "id": "4",
            "name": "4",
            "words": []
        }
    ],
    "words": [],
    "order": ["4", "2", "0", "1", "3"],
    "meta": {
        "time_per_round": 25,
        "words_per_player": 2,
        "skip_count": 0
    }
}
'''

TOTAL_UPDATE = '''{
    "updated_players": [
        {
            "id": "2",
            "name": "2new",
            "words": []
        },
        {
            "id": "3",
            "name": "3new",
            "words": []
        }
    ],
    "updated_order": ["4", "2", "0", "1", "3"],
    "updated_meta": {
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
        request = webapp2.Request.blank('/device_id/pregame/create')
        request.method = 'POST'
        request.body = "json=%s" % GAME_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        return json_returned['id'], str(json_returned['pin'])

    def test_create(self):
        self.create_game()
        self.assertEqual(len([PreGame.query()]), 1)
        now_json = PreGame.query().fetch(1)[0].game_json
        need_game = json.loads(GAME_ON_SERVER_JSON)
        now_game = json.loads(now_json)
        for key in need_game:
            self.assertEqual(need_game[key], now_game[key])

    def test_get(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/%s' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        was_game = json.loads(GAME_JSON)
        now_game = json.loads(response.body)
        for key in was_game:
            self.assertEqual(was_game[key], now_game[key])
        request = webapp2.Request.blank('/other_device_id/pregame/%s' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_update(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        need_game = json.loads(GAME_JSON_AFTER_UPDATE)
        now_game = json.loads(response.body)
        for key in need_game:
            self.assertEqual(need_game[key], now_game[key])
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_version(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = 'json=%s' % UPDATE_JSON
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
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_id/pregame/%s/since/%d' % (game_id, first_version))
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        need_diff = json.loads(SINCE_JSON)
        now_diff = json.loads(response.body)
        for key in need_diff:
            self.assertEqual(need_diff[key], now_diff[key])

    def test_start(self):
        game_id, game_pin = self.create_game()
        self.assertTrue(PreGame.query().fetch(1)[0].can_update)
        request = webapp2.Request.blank('/device_id/pregame/%s/start' % game_id)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertFalse(PreGame.query().fetch(1)[0].can_update)
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_abort(self):
        game_id, game_pin = self.create_game()
        self.assertTrue(PreGame.query().fetch(1)[0].can_update)
        request = webapp2.Request.blank('/device_id/pregame/%s/abort' % game_id)
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertFalse(PreGame.query().fetch(1)[0].can_update)
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_join(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)
        request = webapp2.Request.blank('/other_device_id/pregame/join')
        request.method = 'POST'
        request.body = "json=%s" % json.dumps({"pin": game_pin})
        response = request.get_response(main.app)
        need_json = json.loads(JSON_JOIN)
        response_struct = json.loads(response.body)
        now_json = json.loads(response_struct['game'])
        for key in need_json['game']:
            if key != "pin":
                self.assertEqual(need_json['game'][key], now_json[key])
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % UPDATE_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_current_game(self):
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/get_current_game')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(json.loads(response.body), [game_id])
        request = webapp2.Request.blank('/other_device_id/pregame/join')
        request.method = 'POST'
        request.body = "json=%s" % json.dumps({"pin": game_pin})
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/other_device_id/pregame/get_current_game')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(json.loads(response.body), [game_id])
        game_id, game_pin = self.create_game()
        request = webapp2.Request.blank('/device_id/pregame/get_current_game')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(json.loads(response.body), [game_id])

    def test_all_1(self):
        request = webapp2.Request.blank('/device_id/pregame/create')
        request.method = 'POST'
        request.body = "json=%s" % GAME_BIG_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        game_id = json_returned['id']
        game_pin = str(json_returned['pin'])
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % BIG_UPDATE_1
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/other_device_id/pregame/join')
        request.method = 'POST'
        request.body = "json=%s" % json.dumps({"pin": game_pin})
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % BIG_UPDATE_2
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
        for key in need_diff:
            self.assertEqual(need_diff[key], now_diff[key])

    def test_all_2(self):
        request = webapp2.Request.blank('/device_id/pregame/create')
        request.method = 'POST'
        request.body = "json=%s" % GAME_BIG_JSON
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        game_id = json_returned['id']
        game_pin = str(json_returned['pin'])
        request = webapp2.Request.blank('/device_id/pregame/%s/version' % game_id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        first_version = json.loads(response.body)['version']
        request = webapp2.Request.blank('/device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % BIG_UPDATE_2
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/other_device_id/pregame/join')
        request.method = 'POST'
        request.body = "json=%s" % json.dumps({"pin": game_pin})
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/other_device_id/pregame/%s/update' % game_id)
        request.method = 'POST'
        request.body = "json=%s" % BIG_UPDATE_1
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
        for key in need_diff:
            self.assertEqual(need_diff[key], now_diff[key])

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()
