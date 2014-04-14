__author__ = 'ivan'


import unittest2
import json
import base64
from google.appengine.ext import testbed
from tests.base_functions import *
from objects.user_devices import User
import main


class UserAPITest(unittest2.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

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

    def test_get_empty(self):
        request = make_request("/aaa/api/linkdevice", "POST", True)
        response = request.get_response(main.app)
        self.run_tasks(1)

        request = make_request("/api/user/get/all", "GET", True)
        request.headers['TheHat-Device-Identity'] = 'aaa'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(json.loads(response.body), {'json': {}, 'version': 0})

    def add(self, to_add, admin, device_id):
        request = make_request("/api/user/update", "POST", admin, "json={0}".format(to_add))
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        return response

    def get(self, device_id):
        request = make_request("/api/user/get/all", "GET", True)
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        return response

    def assign_device(self, device_id):
        request = make_request("/{0}/api/linkdevice".format(device_id), "POST", True)
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEquals(response.status_int, 200)
        self.run_tasks(1)

    def delete(self, to_delete, device_id):
        request = make_request("/api/user/delete", "POST", True, "json={0}".format(to_delete))
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)


    def test_update(self):
        #assign device aaa with default user
        self.assign_device('aaa')

        #add first params from this device
        self.add('{"name": "petya", "sis": "true"}', False, 'aaa')

        response = self.get("aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "petya", "sis": "true"}, "version": 1})

        self.add('{"ttt": "a", "ahaha": "b", "name": "vasya"}', False, 'aaa')

        response = self.get("aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "vasya", "sis": "true", "ttt": "a", "ahaha": "b"},
                                                     "version": 2})
        self.delete('["ttt", "ffff"]', 'aaa')

        response = self.get("aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "vasya", "sis": "true", "ahaha": "b"},
                                                     "version": 3})

