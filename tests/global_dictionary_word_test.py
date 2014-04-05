__author__ = 'ivan'

import webapp2
from objects.global_dictionary_word import GlobalDictionaryWord
from objects.GlobalDictionaryJSON import GlobalDictionaryJson
from google.appengine.ext import testbed
from google.appengine.ext import ndb
from tests.base_functions import *
import unittest2
import time
import main
import json
import base64
import time
from datetime import datetime

class GlobalDictionaryWordTest(unittest2.TestCase):
    @staticmethod
    def post(url, content):
        request = make_request(url, "POST", True, content)
        return request.get_response(main.app)

    def run_tasks(self, count):
        tasks = self.taskqueue_stub.GetTasks("default")
        self.assertEqual(len(tasks), count)
        responses = []
        for task in tasks:
            params = base64.b64decode(task["body"])
            responses.append(GlobalDictionaryWordTest.post(task["url"], params))
        self.taskqueue_stub.FlushQueue("default")
        return responses

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def test_add(self):
        request = make_request("/internal/global_dictionary/add_words/task_queue", "POST", True, 'json=["a", "b", "c"]')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(GlobalDictionaryWord.query().count(), 3)
        request = make_request("/admin/global_dictionary/add_words", "POST", True, 'json=["a", "b", "d"]')
        response = request.get_response(main.app)
        task_response = self.run_tasks(1)
        must_be = [{"E": 50.0, "U": 0, "word": "a", "tags": ""},
                   {"E": 50.0, "U": 0, "word": "b", "tags": ""},
                   {"E": 50.0, "U": 0, "word": "c", "tags": ""},
                   {"E": 50.0, "U": 0, "word": "d", "tags": ""}]
        self.assertEqual(task_response[0].status_int, 200)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(GlobalDictionaryWord.query().count(), 4)
        self.assertEqual(GlobalDictionaryJson.query().count(), 0)

        request = make_request("/admin/global_dictionary/update_json", "POST", True, '0')
        response = request.get_response(main.app)
        task_response = self.run_tasks(1)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(GlobalDictionaryWord.query().count(), 4)
        self.assertEqual(GlobalDictionaryJson.query().count(), 1)
        self.assertEqual(task_response[0].status_int, 200)

        server_json = json.loads(GlobalDictionaryJson.query().get().json)
        self.assertEqual(len(must_be), len(server_json))
        for i in must_be:
            ok = False
            for j in server_json:
                if i["E"] == j["E"] and i["word"] == j["word"] and i["tags"] == j["tags"]:
                    ok = True
                    break
            self.assertTrue(ok)

        request = make_request("/api/global_dictionary/get_words/0", "GET", True, '0')
        response = request.get_response(main.app)
        server_json = json.loads(response.body)

        timestamp = server_json["timestamp"]
        words_time = datetime.fromtimestamp(0)
        for word in GlobalDictionaryWord.query().fetch():
            words_time = max(words_time, word.timestamp)
        self.assertEqual(time.mktime(words_time.timetuple()) * 1000, timestamp)
        self.assertEqual(len(must_be), len(server_json["words"]))

        for i in must_be:
            ok = False
            for j in server_json["words"]:
                if i["E"] == j["E"] and i["word"] == j["word"] and i["tags"] == j["tags"]:
                    ok = True
                    break
            self.assertTrue(ok)

        request = make_request("/api/global_dictionary/get_words/{0}".format(timestamp), "GET", True, '0')
        response = request.get_response(main.app)
        self.assertEqual(json.loads(response.body)["words"], [])
        self.assertEqual(json.loads(response.body)["timestamp"], timestamp)
        time.sleep(1)
        request = make_request("/admin/global_dictionary/add_words", "POST", True, 'json=["f", "g", "h"]')
        request.get_response(main.app)
        task_response = self.run_tasks(1)
        self.assertEqual(task_response[0].status_int, 200)

        request = make_request("/admin/global_dictionary/update_json", "POST", True, '0')
        request.get_response(main.app)
        task_response = self.run_tasks(1)
        self.assertEqual(task_response[0].status_int, 200)

        self.assertEqual(GlobalDictionaryWord.query().count(), 7)
        self.assertEqual(GlobalDictionaryJson.query().count(), 2)

        request = make_request("/api/global_dictionary/get_words/0", "GET", True, '0')
        response = request.get_response(main.app)

        self.assertEqual(len(json.loads(response.body)["words"]), 7)

    def test_more(self):
        request = make_request("/admin/global_dictionary/add_words",
                               "POST", True,
                               'json={0}'.format(json.dumps(["a{0}".format(i) for i in range(201)])))
        response = request.get_response(main.app)
        task_response = self.run_tasks(1)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(task_response[0].status_int, 200)
        self.assertEqual(GlobalDictionaryWord.query().count(), 201)

        request = make_request("/admin/global_dictionary/update_json", "POST", True, '0')
        response = request.get_response(main.app)
        task_response = self.run_tasks(1)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(GlobalDictionaryWord.query().count(), 201)
        self.assertEqual(GlobalDictionaryJson.query().count(), 1)
        self.assertEqual(task_response[0].status_int, 200)

        request = make_request("/api/global_dictionary/get_words/0", "GET", True, '0')
        response = request.get_response(main.app)
        server_json = json.loads(response.body)

        timestamp = server_json["timestamp"]
        words_time = datetime.fromtimestamp(0)
        for word in GlobalDictionaryWord.query().fetch():
            words_time = max(words_time, word.timestamp)
        self.assertEqual(time.mktime(words_time.timetuple()) * 1000, timestamp)
        self.assertEqual(201, len(server_json["words"]))

    def test_get_page(self):
        request = make_request("/admin/global_dictionary/add_words", "GET", False)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 302)
        request = make_request("/admin/global_dictionary/add_words", "GET", True)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_delete(self):
        url = "/admin/global_dictionary/delete"
        request = make_request(url, "POST", True, '0')
        response = request.get_response(main.app)
        task_response = self.run_tasks(1)
        self.assertEqual(GlobalDictionaryWord.query().count(), 0)
        self.assertEqual(GlobalDictionaryJson.query().count(), 0)


    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
