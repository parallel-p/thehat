__author__ = 'ivan'


import unittest2
import json
import base64
from google.appengine.ext import testbed
from tests.base_functions import *
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

        request = make_request("/api/settings/user/get/all", "GET", True)
        request.headers['TheHat-Device-Identity'] = 'aaa'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(json.loads(response.body), {'json': {}, 'version': 0})

    def add(self, api_type, to_add, admin, device_id):
        request = make_request("/api/settings/{0}/update".format(api_type), "POST", admin, "json={0}".format(json.dumps(to_add)))
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        return response

    def get(self, api_type, device_id):
        request = make_request("/api/settings/{0}/get/all".format(api_type), "GET", True)
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

    def delete(self, api_type, to_delete, device_id):
        request = make_request("/api/settings/{0}/delete".format(api_type), "POST", True, "json={0}".format(json.dumps(to_delete)))
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def get_version(self, api_type, device_id):
        request = make_request("/api/settings/{0}/version".format(api_type), "GET", True)
        request.headers['TheHat-Device-Identity'] = device_id
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        return response

    def test_update(self):
        #assign device aaa with default user
        self.assign_device('aaa')

        #add first params from this device
        self.add("user", {"name": "petya", "sis": "true"}, False, 'aaa')

        response = self.get("user", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "petya", "sis": "true"}, "version": 1})

        self.add("user", {"ttt": "a", "ahaha": "b", "name": "vasya"}, False, 'aaa')

        response = self.get("user", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "vasya", "sis": "true", "ttt": "a", "ahaha": "b"},
                                                     "version": 2})
        self.delete("user", ["ttt", "ffff"], 'aaa')

        response = self.get("user", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "vasya", "sis": "true", "ahaha": "b"},
                                                     "version": 3})
        response = self.get_version("user", "aaa")
        self.assertEquals(response.body, '3')

        #and with second device

        self.assign_device('bbb')
        self.add("user", {"a": "1", "name": "kostya"}, False, 'bbb')
        response = self.get_version("user", "aaa")
        self.assertEquals(response.body, '4')
        response = self.get_version("user", "bbb")
        self.assertEquals(response.body, '4')

        response = self.get("user", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "kostya", "sis": "true", "ahaha": "b", "a": "1"},
                                                     "version": 4})

    def test_device(self):
        #assign device aaa with default user
        self.assign_device('aaa')

        #add first params from this device
        self.add("device", {"name": "petya", "sis": "true"}, False, 'aaa')

        response = self.get_version("device", "aaa")
        self.assertEquals(response.body, '1')

        response = self.get("device", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "petya", "sis": "true"}, "version": 1})

        self.add("device", {"ttt": "a", "ahaha": "b", "name": "vasya"}, False, 'aaa')

        response = self.get("device", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "vasya", "sis": "true", "ttt": "a", "ahaha": "b"},
                                                     "version": 2})
        self.delete("device", ["ttt", "ffff"], 'aaa')

        response = self.get("device", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"name": "vasya", "sis": "true", "ahaha": "b"}, "version": 3})
        response = self.get_version("device", "aaa")
        self.assertEquals(response.body, '3')

        #and with second device

        self.assign_device('bbb')
        self.add("device", {"a": "1", "b": "2"}, False, 'bbb')
        response = self.get("device", "bbb")
        self.assertEqual(json.loads(response.body), {"json": {"a": "1", "b": "2"}, "version": 1})

        response = self.get_version("device", "bbb")
        self.assertEquals(response.body, '1')

    def test_devices(self):
        self.assign_device('aaa')

        self.add("user_devices", {"aaa": {"name": "petya", "sis": "true"}}, False, 'aaa')
        response = self.get_version("user_devices", "aaa")
        self.assertEquals(response.body, '1')

        response = self.get("user_devices", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"aaa": {"name": "petya", "sis": "true"}}, "version": 1})

        self.add("user_devices", {"aaa": {"name": "vasya", "a": "t1"}}, False, 'aaa')

        response = self.get("user_devices", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"aaa": {"name": "vasya", "sis": "true", "a": "t1"}}, "version": 2})

        self.add("user_devices", {"bbb": {"name": "vasya", "a": "t1"}}, False, 'aaa')
        response = self.get_version("user_devices", "aaa")
        self.assertEquals(response.body, '3')

        self.assign_device('bbb')

        self.add("user_devices", {"bbb": {"name": "vasya", "a": "t1"}}, False, 'aaa')

        response = self.get("user_devices", "aaa")
        self.assertEqual(json.loads(response.body), {"json": {"aaa": {"name": "vasya", "sis": "true", "a": "t1"}, "bbb": {"name": "vasya", "a": "t1"}}, "version": 4})

        response = self.get("user_devices", "bbb")
        self.assertEqual(json.loads(response.body), {"json": {"aaa": {"name": "vasya", "sis": "true", "a": "t1"}, "bbb": {"name": "vasya", "a": "t1"}}, "version": 4})
        response = self.get_version("user_devices", "aaa")
        self.assertEquals(response.body, '4')

        self.delete("user_devices", {"aaa": ["a", "ffff"]}, 'ccc')
        response = self.get_version("user_devices", "aaa")
        self.assertEquals(response.body, '4')

        self.delete("user_devices", {"aaa": ["a", "ffff"]}, 'bbb')
        response = self.get_version("user_devices", "aaa")
        self.assertEquals(response.body, '5')

        response = self.get("user_devices", "bbb")
        self.assertEqual(json.loads(response.body), {"json": {"aaa": {"name": "vasya", "sis": "true"}, "bbb": {"name": "vasya", "a": "t1"}}, "version": 5})