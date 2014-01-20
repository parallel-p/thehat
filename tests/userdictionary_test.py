import unittest

import json
import webapp2
from google.appengine.ext import testbed

import main
import handlers.userdictionary
from objects.user_dictionary_word import UserDictionaryWord


class UserDictionaryTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_post(self):
        request_data= ['''{"version": 1, "words": [{"word": "word_1", "version": 0, "status": "ok"}, {"word": "word2", "version": "10", "status": "deleted"}]}''',
            '''{"version": 2, "words": [{"word": "word_1", "version": 0, "status": "deleted"}, {"word": "word2", "version": "10", "status": "deleted"}]}''']
        version = 0
        for el in request_data:
            request = webapp2.Request.blank('/123/api/udict')
            request.body = "json={}".format(el)
            request.method = "POST"
            response = request.get_response(main.app)
            version += 1
            a = response.text
            self.assertEqual(int(a), version)

    def test_get(self):
        new_words = ["hat", "cat", "rat"]
        for word in new_words:
            UserDictionaryWord(word=word, version=57, user="device_123").put()
        old_words = ["son", "run"]
        for word in old_words:
            UserDictionaryWord(word=word, version=56, user="device_123").put()
        request = webapp2.Request.blank('/123/api/udict/since/56')
        request.method = "GET"
        response = request.get_response(main.app)
        diff = json.loads(response.body)
        self.assertEqual(diff["version"], 57)
        self.assertEqual(len(diff["words"]), 3)
        self.assertIn(diff["words"][0]["word"], new_words)
        self.assertEqual(response.status_int, 200)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()


    #active -> status
    #1 -> ok
    #2 -> deleted
