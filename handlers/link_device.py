__author__ = 'denspb'

from google.appengine.api import users
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from handlers.base_handlers.api_request_handlers import AuthorizedAPIRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from objects.user_devices import get_user
from handlers.userdictionary import merge_user_dictionary_data


class LinkDevice(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(LinkDevice, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        user = users.get_current_user()
        if user is None:
            self.abort(403)
        key = get_user(user)
        taskqueue.add(url='/internal/linkdevice', params={'user_key': key.id(), 'device_key': self.device_key.id()},
                      countdown=5)
        self.response.write(self.device_id)


class LinkDeviceMaintainConsistency(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(LinkDeviceMaintainConsistency, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        user = ndb.Key('User', int(self.request.get('user_key')))
        device = ndb.Key('Device', int(self.request.get('device_key')))
        merge_user_dictionary_data(user, device)
        user = user.get()
        user.devices.append(device)
        user.put()
        self.response.set_status(200)
