import unittest

import webapp2
from google.appengine.ext import testbed

import main


class TestWordsUpload(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_post(self):
        first_game = '''{"version": 1, "words": [{"word": "word_1", "version": 0, "status": "ok", "index": 0}, {"word": "word2", "version": "10", "status": "deleted", "index":1}]}'''
        second_game = '''{"version": 2, "words": [{"word": "word_1", "version": 0, "status": "deleted", "index": 0}, {"word": "word2", "version": "10", "status": "deleted", "index":1}]}'''
        request = webapp2.Request.blank('/123/udict/update/')
        request.body = "json=" + first_game
        request.method = "POST"
        response = request.get_response(main.app)
        a = response.text
        request = webapp2.Request.blank('/123/udict/update/')
        request.body = "json=" + second_game
        request.method = "POST"
        response = request.get_response(main.app)
        b = response.text
        self.assertTrue(int(a) < int(b))

    def test_get(self):
        request = webapp2.Request.blank('/123/udict/get/')
        request.method = "GET"
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()


    #active -> status
    #1 -> ok
    #2 -> deleted