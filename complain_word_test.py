__author__ = 'ivan'
import json

import webapp2
from google.appengine.ext import testbed
import unittest2

from objects.complained_word import ComplainedWord
import main


class complain_word_test(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_post(self):
        word1 = {"word": "vasya", "reason": "1",
                 "replace_word": "petya"}
        word2 = {"word": "vasya", "reason": "2"}
        len_before = ComplainedWord.all().count()
        request = webapp2.Request.blank('/abc/complain')
        request.body = "complained_words={0}". \
            format(json.dumps([word1, word2]))
        print(json.dumps([word1, word2]))
        request.method = 'POST'
        request.get_response(main.app)
        response = request.get_response(main.app) # It is need to call it twice
        len_after = ComplainedWord.all().count()

        self.assertEqual(response.status_int, 200)
        self.assertEqual(len_after, len_before + 4)

    def test_get_table(self):
        request = webapp2.Request.blank('/abc/complain')
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
