import unittest
import webapp2
import main
import json
from google.appengine.ext import testbed
from google.appengine.ext import ndb

GAME = '''{
    "title": "A game",
    "players": [
        {
            "id": 1,
            "name": "Vasya",
            "words": []
        }
    ],
    "words": [],
    "settings": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1
    },
    "order": [
        1,
        2,
        3
    ]
}
'''
SOME_RES = '{"some_results"}'
SOME_LOG = '{"some_log"}'
URLSAFE = 'agVoZWxsb3IPCxIHQWNjb3VudBiZiwIM'


class TestResults(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def create_game(self):
        request = webapp2.Request.blank('/device_1/pregame/create')
        request.method = 'POST'
        request.body = "json=%s" % GAME
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        return json_returned['id'], json_returned['pin']

    def join(self, device_id, pin):
        request = webapp2.Request.blank('/%s/pregame/join' % device_id)
        request.method = 'POST'
        request.body = "json=%s" % str(pin)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_upload_n_load_results(self):
        request = webapp2.Request.blank('/device_1/upload_results/%s' % URLSAFE)
        request.method = 'POST'
        request.body = 'results=%s' % SOME_RES
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_1/get_results/%s' % URLSAFE)
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body, SOME_RES)

    def test_pregame_upload_n_check_res(self):
        # create 2 games:
        game1_id, game1_pin = self.create_game()
        game2_id, game2_pin = self.create_game()
        self.join('device_2', game1_pin)
        self.join('device_2', game2_pin)

        # check for res, return empty str:
        request = webapp2.Request.blank('/device_1/check_for_results/0')
        request.method = 'GET'
        response = request.get_response(main.app)
        results = json.loads(response.body)['results']
        self.assertEqual(len(results), 0)

        # upload some res from game1:
        request = webapp2.Request.blank('/device_1/upload_results/%s' % game1_id)
        request.method = 'POST'
        request.body = "results=%s" % SOME_RES
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

        # check now - must return nothing but some res
        request = webapp2.Request.blank('/device_1/check_for_results/0')
        request.method = 'GET'
        response = request.get_response(main.app)
        loaded = json.loads(response.body)
        results = loaded['results']
        timestamp = loaded['timestamp']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], SOME_RES)

        # we played second game so push res:
        request = webapp2.Request.blank('/device_1/upload_results/%s' % game2_id)
        request.method = 'POST'
        request.body = "results=%s" % SOME_RES
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

        # now player with id 2 aren't download results:
        request = webapp2.Request.blank('/device_2/check_for_results/0')
        request.method = 'GET'
        response = request.get_response(main.app)
        results = json.loads(response.body)['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], SOME_RES)
        self.assertEqual(results[1], SOME_RES)

        # but player with id 1 already download res of game1:
        request = webapp2.Request.blank('/device_1/check_for_results/%s' % timestamp)
        request.method = 'GET'
        response = request.get_response(main.app)
        results = json.loads(response.body)['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], SOME_RES)

        # and player with id 3 have no access to games:
        request = webapp2.Request.blank('/device_3/check_for_results/0')
        request.method = 'GET'
        response = request.get_response(main.app)
        results = json.loads(response.body)['results']
        self.assertEqual(len(results), 0)

    def test_upload_log(self):
        request = webapp2.Request.blank('/device_1/upload_log/%s' % URLSAFE)
        request.method = 'POST'
        request.body = "log=%s" % SOME_LOG
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        ndb.Key('Log', URLSAFE)

    def test_load_non_existent_res(self):
        request = webapp2.Request.blank('/device_1/get_results/%s' % URLSAFE)
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 404)  # not found

    def TearDown(self):
        self.testbed.deactivate()