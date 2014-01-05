import unittest
import webapp2
import json
import main
from google.appengine.ext import testbed
from objects.dictionaries_packages import PackageDictionary, PackagesStream
from objects.user_devices import get_user_by_device


class PackagesHandlersTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_add_stream_handler(self):
        request = webapp2.Request.blank('/streams/add/stream_id_1/stream_1')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        streams = PackagesStream.query().fetch(2)
        self.assertEqual(len(streams), 1)
        self.assertEqual(streams[0].id, 'stream_id_1')
        self.assertEqual(streams[0].name, 'stream_1')

    def test_add_package_handler(self):
        PackagesStream(id='stream_id_1', name='stream1', packages_id_list=[]).put()
        request = webapp2.Request.blank('/streams/stream_id_1/packages/add/package_id_1/package1/1')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        packages = PackageDictionary.query().fetch(2)
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0].id, 'package_id_1')
        self.assertEqual(packages[0].name, 'package1')
        self.assertEqual(packages[0].release_time, 1)

    def test_change_words_handler(self):
        PackageDictionary(id='package_id_1', name='package1',
                          release_time=1, words=['apple', 'banana']).put()
        request = webapp2.Request.blank('/streams/packages/package_id_1/words')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()
