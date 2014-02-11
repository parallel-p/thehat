import unittest

import json
import webapp2
from google.appengine.ext import testbed

import main
from objects.user_dictionary_word import UserDictionaryWord
from objects.user_devices import get_user_by_device


class UserDictionaryTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.user = get_user_by_device("123")[1]

    def test_post(self):
        REQUEST_DATA = ['''[{"word": "hat", "status": "ok"},
                        {"word": "rat", "status": "deleted"}]''',
                        '''[{"word": "rat", "status": "deleted"},
                        {"word": "drop", "status": "deleted"}]''']
        VERSION_BY_WORD = {"hat": 1, "rat": 2, "drop": 2}
        version = 0
        for el in REQUEST_DATA:
            request = webapp2.Request.blank('/123/api/udict')
            request.body = "json={}".format(el)
            request.method = "POST"
            response = request.get_response(main.app)
            version += 1
            a = response.text
            self.assertEqual(int(a), version)
        words = UserDictionaryWord.query(ancestor=self.user).fetch(4)
        self.assertEqual(len(words), 3)
        for el in words:
            self.assertEqual(VERSION_BY_WORD[el.word], el.version)

    def test_get(self):
        new_words = ["hat", "cat", "rat"]
        for word in new_words:
            UserDictionaryWord(word=word, version=57, parent=self.user).put()
        old_words = ["son", "run"]
        for word in old_words:
            UserDictionaryWord(word=word, version=56, parent=self.user).put()
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
