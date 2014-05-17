__author__ = 'ivan'

import json
import base64

import unittest2
from google.appengine.ext import testbed

from global_dictionary.frequency import WordFrequency
from tests.base_functions import *
import main


class FrequencyDictionaryHandlersTest(unittest2.TestCase):
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
            responses.append(self.post(task["url"], params))
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
        for words, count in [([{"w": "a", "d": "1"}, {"w": "b", "d": "2"}, {"w": "c", "d": "3"}], 3),
                             ([{"w": "t", "d": "1"}, {"w": "y", "d": "2"}, {"w": "c", "d": "3"}], 5)]:
            request = make_request(r'/admin/frequency_dictionary/add', "POST", True,
                                   "json={0}".format(json.dumps(words)))
            response = request.get_response(main.app)
            self.assertEqual(response.status_int, 200)
            task_response = self.run_tasks(1)[0]
            self.assertEqual(task_response.status_int, 200)
            self.assertEqual(WordFrequency.query().count(), count)

    def test_no_admin(self):
        for words, count in [([{"w": "a", "d": "1"}, {"w": "b", "d": "2"}, {"w": "c", "d": "3"}], 0),
                             ([{"w": "t", "d": "1"}, {"w": "y", "d": "2"}, {"w": "c", "d": "3"}], 0)]:
            request = make_request(r'/admin/frequency_dictionary/add', "POST", False,
                                   "json={0}".format(json.dumps(words)))
            response = request.get_response(main.app)
            self.assertEqual(response.status_int, 302)
            self.assertEqual(WordFrequency.query().count(), 0)

    def test_erase(self):
        words = ["a", "b", "c", "d"]
        for i in words:
            WordFrequency(word=i).put()
        self.assertEqual(WordFrequency.query().count(), 4)
        request = make_request(r'/admin/frequency_dictionary/delete', "POST", True)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        task_response = self.run_tasks(1)[0]
        self.assertEqual(task_response.status_int, 200)
        self.assertEqual(WordFrequency.query().count(), 0)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
