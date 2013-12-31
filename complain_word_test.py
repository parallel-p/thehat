__author__ = 'ivan'
import unittest2, webapp2
from google.appengine.ext import testbed
import main

class complain_word_test(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_post(self):
        post_data = '''{
                    'word' = 'vasya',
                    'cause' = '1'
                }'''
        len_before = len(ComplainedWords.all())
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