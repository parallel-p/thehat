import unittest
import json
from random import randint

import webapp2
from google.appengine.ext import testbed
from google.appengine.ext import ndb

import main

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
    "meta": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1,
        "is_public": false
    },
    "order": [
        1
    ]
}
'''
SOME_RES = '{"some_results": "something"}'
SOME_LOG = '{"some_log"}'


def gen_some_urlsafe():
    key = ndb.Key('Trash', randint(1, 100000))
    return key.urlsafe()


class TestResults(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        raise unittest.SkipTest("This module is to be rewrited due to last changes")

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
        request.body = "json=%s" % json.dumps({"pin": str(pin)})
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_upload_n_load_results(self):
        urlsafe = gen_some_urlsafe()
        request = webapp2.Request.blank('/device_1/upload_results/%s' % urlsafe)
        request.method = 'POST'
        request.body = 'json={"results": %s, "is_public": true}' % SOME_RES
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_2/get_results/%s' % urlsafe)
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body, SOME_RES)

    def test_upload_n_load_non_public_results(self):
        urlsafe = gen_some_urlsafe()
        request = webapp2.Request.blank('/device_1/upload_results/%s' % urlsafe)
        request.method = 'POST'
        request.body = 'json={"results": %s, "is_public": false}' % SOME_RES
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_2/get_results/%s' % urlsafe)
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_upload_n_load_non_public_results_by_correct_user(self):
        urlsafe = gen_some_urlsafe()
        request = webapp2.Request.blank('/device_1/upload_results/%s' % urlsafe)
        request.method = 'POST'
        request.body = 'json={"results": %s, "is_public": false}' % SOME_RES
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/device_1/get_results/%s' % urlsafe)
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body, SOME_RES)

    def test_pregame_upload_n_check_res(self):
        # create 2 games:
        game1_id, game1_pin = self.create_game()
        self.join('device_2', game1_pin)
        game2_id, game2_pin = self.create_game()
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
        request.body = 'json={"results": %s, "is_public": false}' % SOME_RES
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
        request.body = 'json={"results": %s, "is_public": false}' % SOME_RES
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

    '''def test_upload_log(self):
        request = webapp2.Request.blank('/device_1/upload_log/some_id')
        request.method = 'POST'
        request.body = "json=%s" % SOME_LOG
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        log = GameLog.query(GameLog.game_id == 'some_id').get()
        self.assertEqual(log.json, SOME_LOG)'''

    def test_load_non_existent_res(self):
        urlsafe = gen_some_urlsafe()
        request = webapp2.Request.blank('/device_1/get_results/%s' % urlsafe)
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 404)  # not found

    def test_save_n_load_game(self):
        request = webapp2.Request.blank('/savegame')
        request.method = 'POST'
        request.body = "json=%s" % SOME_LOG
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 201)
        pin = response.body

        request = webapp2.Request.blank('/savegame/{}'.format(pin))
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body, SOME_LOG)

        request = webapp2.Request.blank('/savegame/bad_pin')
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 404)

    def TearDown(self):
        self.testbed.deactivate()