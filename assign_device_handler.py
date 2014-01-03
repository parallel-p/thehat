__author__ = 'nikolay'

import random
import json

import webapp2
from google.appengine.api import users

from all_handler import AllHandler
from objects.user_devices import *

HTML_BEGIN = '''\
<html>
<head>
<title>Assign device</title>
</head>
<body>
<center>
Enter this pin in application:<br>
'''

HTML_END = '''\
<a href=%s>Logout</a>
</center>
</body>
</html>
'''


class GeneratePinHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user is None:
            self.redirect(users.create_login_url(r'/generate_pin'))
        else:
            pin = random.randint(100000000, 999999999)
            UserPin(user=user, pin=pin).put()
            self.response.write(HTML_BEGIN + ('<h1>%d</h1>' % pin) +
                                HTML_END % users.create_logout_url(r'/generate_pin'))


class AssignDeviceHandler(AllHandler):
    def post(self, **kwargs):
        super(AssignDeviceHandler, self).set_device_id(**kwargs)
        pin = json.loads(self.request.get('pin'))['pin']
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