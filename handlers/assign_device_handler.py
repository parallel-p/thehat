__author__ = 'nikolay'

import json

import webapp2
from google.appengine.api import users
from google.appengine.api import taskqueue

from objects.user_devices import *
from environment import *
from base_handlers.web_request_handler import WebRequestHandler
from base_handlers.api_request_handlers import AuthorizedAPIRequestHandler
from objects.pin_number import PinNumber

class AssignDeviceHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AssignDeviceHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        pin = json.loads(self.request.get('json'))['pin']
        pin = PinNumber.retrive(pin, "assign_device")
        if pin is None:
            self.error(404)
            return
        user_key = pin.data
        taskqueue.add(url='/internal/linkdevice', params={'user_key': user_key.id(),
                                                          'device_key': self.device_key.id()},
                      countdown=5)
        self.response.write(json.dumps({"email": user_key.get().user_object.email()}))
        pin.free(False)


