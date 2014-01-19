import unittest

import json
import webapp2
from google.appengine.ext import testbed

import main
import handlers.userdictionary


class TestWordsUpload(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.dictionary_key = handlers.userdictionary.UserDictionary(user="device_123", id=0).put()

    def test_post(self):
        request_data= ['''{"version": 1, "words": [{"word": "word_1", "version": 0, "status": "ok"}, {"word": "word2", "version": "10", "status": "deleted"}]}''',
            '''{"version": 2, "words": [{"word": "word_1", "version": 0, "status": "deleted"}, {"word": "word2", "version": "10", "status": "deleted"}]}''']
        version = self.dictionary_key.get().version
        for el in request_data:
            request = webapp2.Request.blank('/123/udict/0/update')
            request.body = "json={}".format(el)
            request.method = "POST"
            response = request.get_response(main.app)
            version += 1
            a = response.text
            self.assertEqual(int(a), version)

    def test_get(self):
        dictionary = self.dictionary_key.get()
        dictionary.version = 57
        dictionary.put()
        new_words = ["hat", "cat", "rat"]
        for word in new_words:
            handlers.userdictionary.UserWord(word=word, parent=self.dictionary_key, version=57).put()
        old_words = ["son", "run"]
        for word in old_words:
            handlers.userdictionary.UserWord(word=word, parent=self.dictionary_key, version=56).put()
        request = webapp2.Request.blank('/123/udict/0/get/since/56')
        request.method = "GET"
        response = request.get_response(main.app)
        diff = json.loads(response.body)
        self.assertEqual(diff["version"], 57)
        self.assertEqual(len(diff["words"]), 3)
        self.assertIn(diff["words"][0]["word"], new_words)
        self.assertEqual(response.status_int, 200)

    def test_list(self):
        request = webapp2.Request.blank('/123/udict/list')
        request.method = "GET"
        response = request.get_response(main.app)
        l = json.loads(response.body)
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0]["id"], 0)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()


    #active -> status
    #1 -> ok
    #2 -> deleted
