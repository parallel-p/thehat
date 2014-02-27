__author__ = 'ivan'

import webapp2
from objects.global_dictionary_version import GlobalDictionaryVersion
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.ext import testbed
from base_functions import *
import unittest2

import main


class GlobalDictionaryWordTest(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()

    def test_add(self):
        version = GlobalDictionaryVersion.get_server_version()
        request = make_request("/json_updater","POST", True, "data=ff%0D%0Afff")
        response = request.get_response(main.app)

        version2 = GlobalDictionaryVersion.get_server_version()
        self.assertEqual(response.status_int, 200)
        self.assertEqual(version, version2 - 1)
        self.assertEqual(GlobalDictionaryWord.query().count(), 2)

    def test_get(self):
        request = make_request("/json_updater", "POST", True, "data=ff%0D%0Afff")
        request.get_response(main.app)

        request = make_request("/get_all_words/0", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body.count("E"), 2)

        request = make_request("/get_all_words/2", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body.count("E"), 0)

        request = make_request("/json_updater", "POST", True, "data=ffa%0D%0Afff")
        request.get_response(main.app)
        request = make_request("/get_all_words/0", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body.count("E"), 3)

        request = make_request("/get_all_words/2", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body.count("E"), 1)



    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
