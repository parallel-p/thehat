__author__ = 'ivan'
import json

from generic_handler import GenericHandler
from objects.user_devices import get_device_and_user
from handlers.base_handlers.web_request_handler import WebRequestHandler


class APIRequestHandler(GenericHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)


class AuthorizedAPIRequestHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)
        self.device_id = None
        self.device_key = None
        self.user_key = None

    def dispatch(self):
        self.device_id = (self.request.route_kwargs.get('device_id', None) or
                          self.request.headers.get('TheHat-Device-Identity', None))
        if self.device_id is None:
            self.response.headers.add("WWW-Authenticate", "device-id")
            self.abort(401)
        self.device_key, self.user_key = get_device_and_user(self.device_id)
        super(APIRequestHandler, self).dispatch()


class GetAllValues:

    @staticmethod
    def get(object):
        curr_user = object.get()
        return json.dumps({"json": curr_user.values, "version": curr_user.version})

    class User(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(GetAllValues.User, self).__init__(*args, **kwargs)

        def get(self):
            self.response.write(GetAllValues.get(self.user_key))

    class DevicePrivate(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(GetAllValues.DevicePrivate, self).__init__(*args, **kwargs)

        def get(self):
            self.response.write(GetAllValues.get(self.device_id))


class UpdateValues:
    @staticmethod
    def update(object, to_add):
        curr = object.get()
        add = json.loads(to_add)
        for elem in add:
            curr.values[elem] = add[elem]
        curr.version += 1
        curr.put()

    class User(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(UpdateValues.User, self).__init__(*args, **kwargs)

        def post(self):
            UpdateValues.update(self.user_key, self.request.get("json"))

    class DevicePrivate(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(UpdateValues.DevicePrivate, self).__init__(*args, **kwargs)

        def post(self):
            UpdateValues.update(self.device_key, self.request.get("json"))


class DeleteValues:

    @staticmethod
    def delete(object, to_delete):
        to_delete = json.loads(to_delete)
        curr = object.get()
        for elem in to_delete:
            if elem in curr.values:
                del curr.values[elem]
        curr.version += 1
        curr.put()

    class User(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(DeleteValues.User, self).__init__(*args, **kwargs)

        def post(self):
            DeleteValues.delete(self.user_key, self.request.get("json"))

    class DevicePrivate(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(DeleteValues.DevicePrivate, self).__init__(*args, **kwargs)

        def post(self):
            DeleteValues.delete(self.device_key, self.request.get("json"))


class GetLastUserVersion(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GetLastUserVersion, self).__init__(*args, **kwargs)

    def get(self):
        self.response.write(self.user_key.get().version)


class GetLastPrivateDeviceVersion(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GetLastPrivateDeviceVersion, self).__init__(*args, **kwargs)

    def get(self):
        self.response.write(self.device_key.get().version)
