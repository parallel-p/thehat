import unittest
import json

import webapp2
from google.appengine.ext import testbed

import main
from objects.dictionaries_packages import PackageDictionary, PackagesStream
from objects.user_streams import UserStreams
from objects.user_devices import get_user_by_device


class PackagesHandlersTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.setup_env(user_is_admin='1')
        self.testbed.init_user_stub()

    def test_get_streams_list_handler(self):
        PackagesStream(id='1', name='stream1', packages_id_list=['1', '2']).put()
        PackagesStream(id='2', name='stream2', packages_id_list=['3']).put()

        request = webapp2.Request.blank('/device_id_1/streams')
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
        UserStreams(parent=get_user_by_device('device_id_1')[1], streams=['2', '3']).put()
        request = webapp2.Request.blank(r'/device_id_1/streams/1/to/true')
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_get_packages_list_handler(self):
        PackagesStream(id='1', name='stream1', packages_id_list=['1', '2']).put()
        PackageDictionary(id='1', name='package1', release_time=1, words=['tea', 'coffee']).put()
        PackageDictionary(id='2', name='package2', release_time=2, words=['apple', 'banana']).put()
        request = webapp2.Request.blank(r'/device_id_1/streams/1')
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
        PackageDictionary(id='1', name='package1', release_time=1, words=['tea', 'coffee']).put()
        PackageDictionary(id='2', name='package2', release_time=2, words=['apple', 'banana']).put()
        request = webapp2.Request.blank(r'/device_id_1/streams/packages/1')
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
