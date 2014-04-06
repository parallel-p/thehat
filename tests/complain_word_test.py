import constants

__author__ = 'ivan'
import json

import webapp2
from google.appengine.ext import testbed
import unittest2

from objects.complained_word import ComplainedWord
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.ext import ndb
from tests.base_functions import *
import main
import os


class complain_word_test(unittest2.TestCase):
    @staticmethod
    def setCurrentUser(email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    @staticmethod
    def logoutCurrentUser():
        complain_word_test.setCurrentUser(None, None)

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        #self.testbed.setup_env(USER_EMAIL='usermail@gmail.com', USER_ID='1', USER_IS_ADMIN='true') # it is true way
        complain_word_test.setCurrentUser('usermail@gmail.com', '1', True)  # but it is "hack" way...
        self.testbed.init_user_stub()

    def test_post(self):
        word1 = {constants.complained_word: "vasya",
                 constants.reason: "typo",
                 constants.word_to_replace: "petya"}
        word2 = {constants.complained_word: "vasya",
                 constants.reason: "not_a_noun"}
        len_before = ComplainedWord.query().count()
        request = webapp2.Request.blank('/abc/complain')
        request.body = "json={0}". \
            format(json.dumps([word1, word2]))
        request.method = 'POST'
        request.get_response(main.app)
        response = request.get_response(main.app)  # It is need to call it twice
        len_after = ComplainedWord.query().count()
        self.assertEqual(response.status_int, 200)
        self.assertEqual(len_after, len_before + 4)

    def test_get_table(self):
        word1 = {constants.complained_word: "vasya",
                 constants.reason: "typo",
                 constants.word_to_replace: "petya"}
        word2 = {constants.complained_word: "vasya",
                 constants.reason: "not_a_noun"}
        request = webapp2.Request.blank('/abc/complain')
        request.body = "json={0}". \
            format(json.dumps([word1, word2]))
        request.method = 'POST'
        request.get_response(main.app)
        request = webapp2.Request.blank('/admin/complain/list')
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_erase(self):
        word1 = {constants.complained_word: "vasya",
                 constants.reason: "typo",
                 constants.word_to_replace: "petya"}
        word2 = {constants.complained_word: "kokoko",
                 constants.reason: "not_a_noun"}
        request = webapp2.Request.blank('/abc/complain')
        request.body = "json={0}". \
            format(json.dumps([word1, word2]))
        request.method = 'POST'
        request.get_response(main.app)
        request.get_response(main.app)

        request = webapp2.Request.blank('/admin/complain/cancel')
        request.method = 'POST'
        request.body = "word=vasya"
        len_before = ComplainedWord.query().count()
        response = request.get_response(main.app)

        self.assertEqual(response.status_int, 200)
        len_after = ComplainedWord.query().count()
        self.assertEqual(len_before, len_after + 2)
        request = webapp2.Request.blank('/admin/complain/clear')
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(ComplainedWord.query().count(), 0)

    def test_delete_from_global_dictionary(self):
        words = ["a", "b", "c", "d"]
        for i in words:
            GlobalDictionaryWord(word=i, id=i, tags="").put()
        ComplainedWord(word="c").put()
        ComplainedWord(word="c").put()
        ComplainedWord(word="d").put()
        request = make_request("/admin/complain/remove", "POST", True, 'word=c')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(ComplainedWord.query().count(), 1)
        self.assertEqual(GlobalDictionaryWord.query().count(), 4)
        self.assertEqual(ndb.Key(GlobalDictionaryWord, "c").get().tags, "-deleted")

        ComplainedWord(word="c").put()
        response = request.get_response(main.app)
        self.assertEqual(ComplainedWord.query().count(), 1)
        self.assertEqual(GlobalDictionaryWord.query().count(), 4)
        self.assertEqual(ndb.Key(GlobalDictionaryWord, "c").get().tags, "-deleted")


    def tearDown(self):
        complain_word_test.logoutCurrentUser()
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
