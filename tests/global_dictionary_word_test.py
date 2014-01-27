__author__ = 'ivan'

import webapp2
from google.appengine.ext import testbed
import unittest2

import main


class GlobalDictionaryWordTest(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        self.testbed.setup_env(USER_EMAIL='test@example.com', USER_ID='123', USER_IS_ADMIN='1', overwrite=True)

    '''def test_add(self):
        version = GlobalDictionaryVersion.get_server_version()
        text = "vasya 1 \n petya 22 12\n kolya \n"
        request = webapp2.Request.blank("/edit_words")
        request.body = 'text={0}'.format(text)
        request.method = 'POST'
        response = request.get_response(main.app)
        version2 = GlobalDictionaryVersion.get_server_version()
        self.assertEqual(response.status_int, 302) # not 200, because redirrect
        self.assertEqual(version, version2 - 1)
        self.assertEqual(GlobalDictionaryWord.all().count(), 3)'''

    def test_get(self):
        text = "vasya 1 \n petya 22 12\n kolya \n"
        request = webapp2.Request.blank("/edit_words")
        request.body = 'text={0}'.format(text)
        request.method = 'POST'
        request.get_response(main.app)

        request = webapp2.Request.blank("/get_all_words/2")
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)


    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()