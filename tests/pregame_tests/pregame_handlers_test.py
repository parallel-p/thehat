__author__ = 'ivan'

import unittest2
import webapp2
from google.appengine.ext import testbed
import main
from objects.pregame import *
from tests.pregame_tests.pregame_jsons import CREATE_GAME_JSON


class PregameHandlersTest(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_create_game(self):
        request = webapp2.Request.blank('/device_id/pregame/create')
        request.method = 'POST'
        request.body = "json={0}".format(CREATE_GAME_JSON)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        json_returned = json.loads(response.body)
        first_id = json_returned['id']
        self.assertEqual(int(json_returned['version']), 5)
        response = request.get_response(main.app)
        son_returned = json.loads(response.body)
        self.assertEqual(int(json_returned['version']), 5)
        second_id = json_returned['id']
        self.assertNotEqual(first_id, second_id)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
