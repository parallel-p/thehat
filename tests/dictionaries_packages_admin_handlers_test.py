import unittest

import webapp2
from google.appengine.ext import testbed

import main
from objects.dictionaries_packages import PackageDictionary, PackagesStream


class PackagesHandlersTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        self.testbed.setup_env(USER_EMAIL='test@example.com', USER_ID='123', USER_IS_ADMIN='1', overwrite=True)

    def test_add_stream_handler(self):
        request = webapp2.Request.blank('/streams')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_add_package_handler(self):
        PackagesStream(id='stream_id_1', name='stream1', packages_id_list=[]).put()
        request = webapp2.Request.blank('/streams/stream_id_1/packages/add')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

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
