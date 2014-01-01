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
        word1 = {"device_id": "aaa", "word": "vasya", "cause": "1",
                 "replace_word": "petya"}
        word2 = {"device_id": "aaa", "word": "vasya", "cause": "2"}
        len_before = ComplainedWord.all().count()
        request = webapp2.Request.blank('/abc/complain')
        request.body = "complained_words={0}". \
            format(json.dumps([word1, word2]))
        request.method = 'POST'
        response = request.get_response(main.app)
        len_after = ComplainedWord.all().count()

        self.assertEqual(response.status_int, 200)
        self.assertEqual(len_after, len_before + 2)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
