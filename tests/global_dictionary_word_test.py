__author__ = 'ivan'

import webapp2
from objects.global_dictionary_version import GlobalDictionaryVersion
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.ext import testbed
from tests.base_functions import *
import unittest2

import main
import json


class GlobalDictionaryWordTest(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()

    def test_add(self):
        request = make_request("/internal/global_dictionary/add_words", "POST", True, 'json=["a", "b", "c"]')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(GlobalDictionaryWord.query().count(), 3)

    def test_get(self):
        request = make_request("/internal/global_dictionary/add_words", "POST", True, 'json=["a", "b", "c"]')
        request.get_response(main.app)

        request = make_request("/internal/global_dictionary/update_json", "POST", True, 'timestamp=0')
        response = request.get_response(main.app)
        request = make_request("/api/global_dictionary/get_words/0", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body.count("tags"), 3)
        ts = json.loads(response.body)["timestamp"]

        request = make_request("/internal/global_dictionary/add_words", "POST", True, 'json=["aa", "vb", "cv"]')
        request.get_response(main.app)
        request = make_request("/internal/global_dictionary/update_json", "POST", True, 'timestamp={0}'.format(ts))
        request.get_response(main.app)
        request = make_request("/api/global_dictionary/get_words/0", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.body.count("tags"), 6)


    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
