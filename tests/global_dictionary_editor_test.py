__author__ = 'ivan'

import webapp2
from google.appengine.ext import testbed
import unittest2

import main
import os


class GlobalDictionaryEditorTest(unittest2.TestCase):

    @staticmethod
    def setCurrentUser(email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    @staticmethod
    def logoutCurrentUser():
        GlobalDictionaryEditorTest.setCurrentUser(None, None)

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()

    @staticmethod
    def get_table(body):
        left, right = body.find("<tbody>"), body.find("</tbody>") + 8
        return body[left:right]

    def test_get(self):
        request = webapp2.Request.blank("/global/edit/0")
        GlobalDictionaryEditorTest.setCurrentUser('usermail@gmail.com', '1', False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 302)
        GlobalDictionaryEditorTest.setCurrentUser('usermail@gmail.com', '1', True)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2 , 0)





