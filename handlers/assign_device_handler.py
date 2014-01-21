
__author__ = 'nikolay'

import random
import json

import webapp2
from google.appengine.api import users

from all_handler import AllHandler
from objects.user_devices import *
from environment import *


class GeneratePinHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user is None:
            self.redirect(users.create_login_url('/generate_pin'))
        else:
            pin = str(random.randint(100000000, 999999999))
            UserPin(user=user, pin=pin).put()
            template = JINJA_ENVIRONMENT.get_template('templates/generate_pin.html')
            self.response.write(template.render(
                {"pin_code": pin,
                 "logout_link": users.create_logout_url('/')}))


class AssignDeviceHandler(AllHandler):
    def post(self, **kwargs):
        super(AssignDeviceHandler, self).set_device_id(**kwargs)
        pin = json.loads(self.request.get('json'))['pin']
        user = UserPin.query(UserPin.pin == pin).get()
        if user is None:
            self.error(404)
        else:
            was_device = DeviceUser.query(DeviceUser.device_id == self.device_id).get()
            if was_device is not None:
                was_device.key.delete()
                # TODO: should we do something with old games?
            DeviceUser(device_id=self.device_id, user_id=user.user.user_id()).put()
            self.response.write(json.dumps({"email": user.user.email()}))


class DeleteOldPinsHandler(webapp2.RequestHandler):
    def get(self):
        pins = UserPin.query()
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