__author__ = 'ivan'

import unittest2
import webapp2
from google.appengine.ext import testbed
import main
from objects.pregame import *
from tests.pregame_tests.pregame_jsons import CREATE_GAME_JSON, \
    UPDATE_META_JSON, GAME_JSON, DELETE_PLAYERS_JSON, BROKEN_CREATE_GAME_JSON, \
    BROKEN_DELETE_PLAYERS_JSON, BROKEN_UPDATE_META_JSON


class PregameHandlersTest(unittest2.TestCase):
    @staticmethod
    def make_request(url, method, body=None):
        request = webapp2.Request.blank(url)
        request.method = method
        if body is not None:
            request.body = body
        return request

    @staticmethod
    def make_game(body_json):
        return PregameHandlersTest.make_request('/device_id/pregame/create',
                                                'POST',
                                                "json={0}".format(body_json))

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_create_game(self):
        request = PregameHandlersTest.make_game(CREATE_GAME_JSON)

        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        first_id, first_pin = json_returned['id'], json_returned['pin']
        self.assertEqual(int(json_returned['version']), 5)

        response = request.get_response(main.app)

        json_returned = json.loads(response.body)
        self.assertEqual(int(json_returned['version']), 5)
        second_id, second_pin = json_returned['id'], json_returned['pin']

        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(first_pin, second_pin)

    @unittest2.expectedFailure
    def test_create_game_broken_json(self):
        request = PregameHandlersTest.make_game(BROKEN_CREATE_GAME_JSON)
        response = request.get_response(main.app)
        self.assertEqual(len(PreGame.query().fetch(1)), 0)
        self.assertEqual(response.status_int, 400)

    @unittest2.expectedFailure
    def test_get_game_no_id_in_db(self):
        request = PregameHandlersTest.make_request('/device_id/pregame/agx0ZXN',
                                                   'GET')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 404)

    def test_get_game_from_db(self):
        post_request = PregameHandlersTest.make_game(CREATE_GAME_JSON)
        post_request.get_response(main.app)
        response_json = json.loads(post_request.get_response(main.app).body)
        game_id = response_json['id']

        get_request = PregameHandlersTest.make_request('/device_id/pregame/{0}'.format(game_id),
                                                       'GET')
        get_request.get_response(main.app)
        response_json = json.loads(get_request.get_response(main.app).body)
        self.assertEqual(response_json['game']['title'], "A game")
        self.assertEqual(response_json['game']['version'], 5)
        get_request = PregameHandlersTest.make_request('/other_device_id/pregame/{0}'.format(game_id),
                                                       'GET')
        response = get_request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    @unittest2.expectedFailure
    def test_connect_to_game_broken_pin(self):
        post_request = PregameHandlersTest.make_game(CREATE_GAME_JSON)
        post_request.get_response(main.app)
        body = 'json={0}'.format(json.dumps({"pong": "123"}))
        post_request = PregameHandlersTest.make_request('/new_device_id/pregame/join', 'POST', body)
        response = post_request.get_response(main.app)
        self.assertEqual(response.status_int, 400)

    @unittest2.expectedFailure
    def test_connect_to_game_wrong_pin(self):
        body = 'json={0}'.format(json.dumps({"pin": "123"}))
        post_request = PregameHandlersTest.make_request('/device_id/pregame/join', 'POST', body)
        response = post_request.get_response(main.app)
        self.assertEqual(response.status_int, 403)

    def test_connect_to_game(self):
        post_request = PregameHandlersTest.make_game(CREATE_GAME_JSON)
        pin = json.loads(post_request.get_response(main.app).body)['pin']
        body = 'json={0}'.format(json.dumps({"pin": pin}))
        post_request = PregameHandlersTest.make_request('/new_device_id/pregame/join', 'POST', body)
        response = post_request.get_response(main.app)
        post_request.get_response(main.app)
        create_game = json.loads(CREATE_GAME_JSON)
        server_game = json.loads(response.body)
        self.assertEqual(create_game["players"], server_game["game"]["players"])
        self.assertEqual(create_game["words"], server_game["game"]["words"])
        self.assertEqual(create_game["meta"], server_game["game"]["meta"])
        self.assertEqual(response.status_int, 200)

    @unittest2.expectedFailure
    def test_update_no_game(self):
        post_request = PregameHandlersTest.make_request("/device_id/pregame/11/update", 'POST',
                                                        body="json={0}".format(UPDATE_META_JSON))
        response = post_request.get_response(main.app)
        self.assertEqual(response.status_int, 404)

    @unittest2.expectedFailure
    def test_update_game_wrong_json(self):
        create_game_request = PregameHandlersTest.make_game(GAME_JSON)
        response = json.loads(create_game_request.get_response(main.app).body)
        pin, id = response['pin'], response['id']
        delete_player_request = PregameHandlersTest.make_request('/device_id/pregame/{0}/update'.format(id),
                                                                 'POST', 'json={0}'.format(BROKEN_DELETE_PLAYERS_JSON))
        response = delete_player_request.get_response(main.app)
        self.assertEqual(response.status_int, 400)
        request = PregameHandlersTest.make_request('/device_id/pregame/{0}/update'.format(id),
                                                   'POST', 'json={0}'.format(BROKEN_UPDATE_META_JSON))
        response = request.get_response(main.app)
        self.assertEqual(len(json.loads(PreGame.query().fetch(1)[0].game_json)["meta"], 3))
        self.assertEqual(response.status_int, 400)

    def test_update_game(self):
        create_game_request = PregameHandlersTest.make_game(GAME_JSON)
        response = json.loads(create_game_request.get_response(main.app).body)
        pin, id = response['pin'], response['id']
        delete_player_request = PregameHandlersTest.make_request('/device_id/pregame/{0}/update'.format(id),
                                                                 'POST', 'json={0}'.format(DELETE_PLAYERS_JSON))
        delete_player_request.get_response(main.app)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()