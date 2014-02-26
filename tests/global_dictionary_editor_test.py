__author__ = 'ivan'

import webapp2
from google.appengine.ext import testbed
import unittest2
import json

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
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
        self.testbed.init_user_stub()

    def tearDown(self):
        self.testbed.deactivate()


    @staticmethod
    def get_table(body):
        left, right = body.find("<tbody>"), body.find("</tbody>") + 8
        return body[left:right]

    @staticmethod
    def make_request(url, type, admin = False, body = None):
        request = webapp2.Request.blank(url)
        request.method = type
        if body:
            request.body = body
        GlobalDictionaryEditorTest.setCurrentUser('usermail@gmail.com', '1', admin)
        return request


    @staticmethod
    def push_words(data, admin):
        request = GlobalDictionaryEditorTest.make_request("/json_updater", "POST", admin, data)
        return request.get_response(main.app)

    def test_get_no_data(self):
        request = GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/edit/0", "GET")
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 302)
        GlobalDictionaryEditorTest.setCurrentUser('usermail@gmail.com', '1', True)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2, 0)

    def test_get(self):
        GlobalDictionaryEditorTest.push_words("data=ff%0D%0Afff", True)
        GlobalDictionaryEditorTest.push_words("data=ff%0D%0Afff", True)

        request = GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/edit/0", "GET", True)
        response = request.get_response(main.app)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2, 2)

    def test_get_2_lists(self):
        for i in range(80):
            GlobalDictionaryEditorTest.push_words("data={0}%0D%0A{1}%0D%0A{2}".format(i, str(i) + "d",
                                                                                      str(i) + 'dd'), True)

        request = GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/edit/0", "GET", True)
        response = request.get_response(main.app)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2, 200)

        request = GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/edit/1", "GET", True)
        response = request.get_response(main.app)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2, 40)

    def test_delete_admin(self):
        GlobalDictionaryEditorTest.push_words("data=ff%0D%0Afff", True)
        GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/delete", "POST", True, "word=ff").get_response(main.app)

        request = GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/edit/0", "GET", True)
        response = request.get_response(main.app)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2, 1)

    def test_delete_no_admin(self):
        GlobalDictionaryEditorTest.push_words("data=ff%0D%0Afff", True)
        GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/delete", "POST", False, "word=ff").get_response(main.app)

        request = GlobalDictionaryEditorTest.make_request("/admin/global_dictionary/edit/0", "GET", True)
        response = request.get_response(main.app)
        table = GlobalDictionaryEditorTest.get_table(response.body)
        self.assertEqual(table.count("tr") / 2, 2)









