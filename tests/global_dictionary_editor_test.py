__author__ = 'ivan'

import webapp2
from google.appengine.ext import testbed
import unittest2

import main


class GlobalDictionaryEditorTest(unittest2.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        self.testbed.setup_env(USER_EMAIL='test@example.com', USER_ID='123', USER_IS_ADMIN='1', overwrite=True)

    def test_get(self):
        request = webapp2.Request.blank("/")



