__author__ = 'ivan'

import unittest2
import webapp2
from google.appengine.ext import testbed
import main
from objects.pregame import *
from tests.pregame_tests.pregame_jsons import CREATE_GAME_JSON


class PregameHandlersTest(unittest2.TestCase):

    @staticmethod
    def make_request(url, method, body=None):
        request = webapp2.Request.blank(url)
        request.method = method
        if body is not None:
            request.body = body
        return request

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_create_game(self):
        request = PregameHandlersTest.make_request('/device_id/pregame/create',
                                                   'POST',
                                                   "json={0}".format(CREATE_GAME_JSON))

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
    def test_get_game_no_id_in_db(self):
        request = PregameHandlersTest.make_request('/device_id/pregame/agx0ZXN',
                                               'GET')
        request.get_response(main.app)

    def test_get_game_from_db(self):
        post_request = PregameHandlersTest.\
            make_request('/device_id/pregame/create',
                         'POST',
                         "json={0}".format(CREATE_GAME_JSON))
        post_request.get_response(main.app)
        response_json = json.loads(post_request.get_response(main.app).body)
        game_id = response_json['id']

        get_request = PregameHandlersTest.make_request('/device_id/pregame/{0}'.format(game_id),
                                                       'GET')
        get_request.get_response(main.app)
        response_json = json.loads(get_request.get_response(main.app).body)
        self.assertEqual(response_json['game']['title'], "A game")
        self.assertEqual(response_json['game']['version'], 5)



    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()