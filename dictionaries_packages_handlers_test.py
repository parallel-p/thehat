import unittest

import webapp2
import json
from google.appengine.ext import testbed

import main


class PackagesHandlersTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_get_streams_list_handler(self):
        request = webapp2.Request.blank(r'/a/streams')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        right_json = u'''{
            "streams": [
                {
                    "id": "1",
                    "name": "stream1"
                },
                {
                    "id": "2",
                    "name": "stream2"
                }
            ]
        }
        '''
        right = json.loads(right_json)
        response_struct = json.loads(response.body)
        self.assertEqual(response_struct, right)

    def test_change_stream_state_handler(self):
        request = webapp2.Request.blank(r'/a/streams/stream1/to/true')
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_get_packages_list_handler(self):
        request = webapp2.Request.blank(r'/a/streams/stream1')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        right_json = u'''{
            "packages": [
                {
                    "id": "1",
                    "name": "package1",
                    "release_time": 1
                },
                {
                    "id": "2",
                    "name": "package2",
                    "release_time": 2
                }
            ]
        }
        '''
        right = json.loads(right_json)
        response_struct = json.loads(response.body)
        self.assertEqual(response_struct, right)

    def test_get_package_handler(self):
        request = webapp2.Request.blank(r'/a/streams/packages/package1')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        right_json = u'''{
            "id": "1",
            "name": "package1",
            "release_time": 1,
            "words": [
                "tea",
                "coffee"
            ]
        }
        '''
        right = json.loads(right_json)
        response_struct = json.loads(response.body)
        self.assertEqual(right, response_struct)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()
