__author__ = 'nikolay'
import unittest

from google.appengine.ext import testbed

import main
from handlers.assign_device_handler import *


class AssignDeviceTestCase(unittest.TestCase):
    pin = None

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.setup_env(
            USER_EMAIL='test@example.com',
            USER_ID='123',
            USER_IS_ADMIN='1',
            overwrite=True)
        self.testbed.init_user_stub()
        self.device = Device(device_id='123').put()
        self.taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def test_assign_device(self):
        def _render(x, pin):
            self.pin = pin
        GeneratePinHandler.render = _render
        request = webapp2.Request.blank('/assign_device/generate_pin')
        request.method = "GET"
        request.get_response(main.app)
        self.user = User.query(User.user_id == '123').get(keys_only=True)
        request = webapp2.Request.blank('/123/assign_device')
        request.method = "POST"
        request.body = 'json={"pin": "%s"}' % self.pin
        response = request.get_response(main.app)
        self.assertEqual(response.status_code, 200)
        tasks = self.taskq.get_filtered_tasks(url='/internal/linkdevice')
        self.assertEqual(1, len(tasks))
        request = webapp2.Request.blank(tasks[0].url)
        request.method = "POST"
        request.body = tasks[0].payload
        response = request.get_response(main.app)
        self.assertEqual(response.status_code, 200)
        device, user_after = get_device_and_user('123')
        self.assertEqual(user_after, self.user)