__author__ = 'ivan'

import json

import webapp2
from google.appengine.ext import testbed
import unittest2

from objects.complained_word import ComplainedWord
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.ext import ndb
from tests.base_functions import *
import main
import os


class complain_word_test(unittest2.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()

    def test_get_admin(self):
        request = make_request("/admin", "GET", True)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_get_no_admin(self):
        request = make_request("/admin", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 302)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()