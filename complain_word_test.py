__author__ = 'ivan'
import json

import webapp2
from google.appengine.ext import testbed

import unittest2
import main


class complain_word_test(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_post(self):
        data = []
        word = {"device_id": "aaa", "word": "vasya", "cause": "1", "replace_word": "petya"}
        data.append(word)
        data.append(word)
        post_data = {"complained_words": json.dumps(data)}
        len_before = len(ComplainedWords.all())
        print(post_data)
        request = webapp2.Request.blank('/abc/complain', None, None, post_data)
        request.method = 'POST'
        response = request.get_response(main.app)
        len_after = len(ComplainedWords.all())
        self.assertEqual(response.status_int, 200)
        self.assertEqual(len_after, len_before - 1)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()