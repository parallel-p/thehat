__author__ = 'nikolay'
import unittest

from google.appengine.ext import testbed

import main
from objects.user_devices import *
from handlers.assign_device_handler import *


class AssignDeviceTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.setup_env(
            USER_EMAIL='test@example.com',
            USER_ID='123',
            USER_IS_ADMIN='0',
            overwrite=True)
        self.testbed.init_user_stub()
        self.device = Device(device_id='123').put()

    def test_assign_device(self):
        def _render(x, pin):
            self.pin = pin
        GeneratePinHandler.render = _render
        request = webapp2.Request.blank('/generate_pin')
        request.method = "GET"
        request.get_response(main.app)
        self.user = User.query(User.user_id == '123').get(keys_only=True)
        request = webapp2.Request.blank('/123/assign_device')
        request.method = "POST"
        request.body = 'json={"pin": "%s"}' % self.pin
        response = request.get_response(main.app)
        self.assertEqual(response.status_code, 200)
        device, user_after = get_device_and_user('123')
        self.assertEqual(user_after, self.user)