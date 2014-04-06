import unittest

import json
import webapp2
from google.appengine.ext import testbed, ndb

import main
from objects.user_dictionary_word import UserDictionaryWord
from objects.user_devices import get_device_and_user, User, Device


class UserDictionaryTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.device, self.user = get_device_and_user("123")

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
        words = UserDictionaryWord.query(self.user).fetch(4)
        self.assertEqual(len(words), 3)
        for el in words:
            self.assertEqual(VERSION_BY_WORD[el.word], el.version)

    def test_get(self):
        new_words = ["hat", "cat", "rat"]
        for word in new_words:
            UserDictionaryWord(word=word, version=57, owner=self.device).put()
        old_words = ["son", "run"]
        for word in old_words:
            UserDictionaryWord(word=word, version=56, owner=self.device).put()
        request = webapp2.Request.blank('/123/api/udict/since/56')
        request.method = "GET"
        response = request.get_response(main.app)
        diff = json.loads(response.body)
        self.assertEqual(diff["version"], 57)
        self.assertEqual(len(diff["words"]), 3)
        self.assertIn(diff["words"][0]["word"], new_words)
        self.assertEqual(response.status_int, 200)

    def test_different_users_iteraction(self):
        devices = [Device(device_id='d{}'.format(i)).put() for i in range(4)]
        users = [User(devices=[devices[1], devices[2]]).put(), User(devices=[devices[3]]).put()]
        for i in range(4):
            request = webapp2.Request.blank('/d{}/api/udict'.format(i))
            request.body = 'json=[{"word": "%s", "status": "ok"}]' % i
            request.method = "POST"
            request.get_response(main.app)
        expected_counts = [1, 2, 2, 1]
        for i in range(4):
            request = webapp2.Request.blank('/d{}/api/udict'.format(i))
            request.method = "GET"
            response = request.get_response(main.app)
            diff = json.loads(response.body)
            self.assertEqual(len(diff["words"]), expected_counts[i],
                             msg="count mismatch with device {}. expected {} found {}".format(i, expected_counts[i], len(diff["words"])))

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()
