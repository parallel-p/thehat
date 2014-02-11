__author__ = 'nikolay'

import random
import json
import time

import webapp2
from google.appengine.api import users

from objects.user_devices import *
from environment import *
from base_handlers.web_request_handler import WebRequestHandler
from base_handlers.api_request_handlers import AuthorizedAPIRequestHandler
from objects.pin_number import PinNumber


class GeneratePinHandler(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GeneratePinHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        user = users.get_current_user()
        user_key = User.query(User.user == user).get(keys_only=True) or User(user=user).put().key
        pin = PinNumber("assign_device", user_key, 60*60*24)
        template = JINJA_ENVIRONMENT.get_template('templates/generate_pin.html')
        self.response.write(template.render(
            {"pin_code": pin,
             "logout_link": users.create_logout_url('/')}))


class AssignDeviceHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AssignDeviceHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        super(AssignDeviceHandler, self).authorizate(*args, **kwargs)
        pin = json.loads(self.request.get('json'))['pin']
        pin = PinNumber.retrive(pin, "assign_device")
        if pin is None:
            self.error(404)
            return
        user = pin.data.get()
        device = self.device_key
        device.parent = user.key
        device.put()
        self.response.write(json.dumps({"email": user.user.email()}))
        pin.free()


assign_device_routes = [
    (r'/generate_pin', GeneratePinHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/assign_device/',
                  handler=AssignDeviceHandler,
                  name='assign_device'),
]
