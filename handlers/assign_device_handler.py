__author__ = 'nikolay'

import random
import json
import time

import webapp2
from google.appengine.api import users

from objects.user_devices import *
from environment import *
from base_handlers.service_request_handler import ServiceRequestHandler
from base_handlers.web_request_handler import WebRequestHandler


class GeneratePinHandler(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GeneratePinHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        user = users.get_current_user()
        pin = str(random.randint(100000000, 999999999))
        UserPin(user=user, pin=pin, time=int(time.time())).put()
        template = JINJA_ENVIRONMENT.get_template('templates/generate_pin.html')
        self.response.write(template.render(
            {"pin_code": pin,
             "logout_link": users.create_logout_url('/')}))


class AssignDeviceHandler(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AssignDeviceHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        pin = json.loads(self.request.get('json'))['pin']
        user = UserPin.query(UserPin.pin == pin).get()
        was_device = DeviceUser.query(DeviceUser.device_id == self.device_id).get()
        if was_device is not None:
            was_device.key.delete()
            # TODO: should we do something with old games?
        DeviceUser(device_id=self.device_id, user_id=user.user.user_id()).put()
        self.response.write(json.dumps({"email": user.user.email()}))


class DeleteOldPinsHandler(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteOldPinsHandler, self).__init__(*args, **kwargs)

    def post(self):
        pins = UserPin.query(UserPin.time < int(time.time()) - 30 * 60) # 30 minutes
        for pin in pins:
            pin.key.delete()


assign_device_routes = [
    (r'/generate_pin', GeneratePinHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/assign_device',
                  handler=AssignDeviceHandler,
                  name='assign_device'),
    webapp2.Route(r'/clean_up/assign_pins',
                  handler=DeleteOldPinsHandler,
                  name='clean_assign_pins')
]
