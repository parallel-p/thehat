__author__ = 'nikolay'

import json

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
        user_key = User.query(User.user_id == user.user_id()).get(keys_only=True) or User(user_id=user.user_id(),
                                                                                          user_object=user).put()
        pin = PinNumber.generate("assign_device", user_key, 60*60*24)
        self.render(pin)

    def render(self, pin):
        template = JINJA_ENVIRONMENT.get_template('templates/generate_pin.html')
        self.response.write(template.render(
            {"pin_code": pin,
             "logout_link": users.create_logout_url('/')}))


class AssignDeviceHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AssignDeviceHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        pin = json.loads(self.request.get('json'))['pin']
        pin = PinNumber.retrive(pin, "assign_device")
        if pin is None:
            self.error(404)
            return
        user = pin.data.get()
        user.devices.append(self.device_key)
        user.put()
        self.response.write(json.dumps({"email": user.user_object.email()}))
        pin.free(False)


assign_device_routes = [
    (r'/generate_pin', GeneratePinHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/assign_device',
                  handler=AssignDeviceHandler,
                  name='assign_device'),
]
