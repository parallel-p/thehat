__author__ = 'ivan'
import json

from generic_handler import GenericHandler
from objects.user_devices import get_device_and_user
import logging


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
        curr_obj = object.get()
        return json.dumps({"json": curr_obj.values, "version": curr_obj.version})

    class User(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(GetAllValues.User, self).__init__(*args, **kwargs)

        def get(self):
            self.response.write(GetAllValues.get(self.user_key))

    class Device(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(GetAllValues.Device, self).__init__(*args, **kwargs)

        def get(self):
            self.response.write(GetAllValues.get(self.device_key))

    class Devices(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(GetAllValues.Devices, self).__init__(*args, **kwargs)

        def get(self):
            curr_user = self.user_key.get()
            if curr_user is None:
                self.error(403)
            self.response.write(json.dumps({"json": curr_user.devices_values, "version": curr_user.devices_version}))


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

    class Device(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(UpdateValues.Device, self).__init__(*args, **kwargs)

        def post(self):
            UpdateValues.update(self.device_key, self.request.get("json"))

    class Devices(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(UpdateValues.Devices, self).__init__(*args, **kwargs)

        def post(self, *args, **kwargs):
            curr_user = self.user_key.get()
            if curr_user is None:
                self.error(403)
            this_user_devices = [device.get().device_id for device in curr_user.devices]
            add = json.loads(self.request.get("json"))
            for device_id in add:
                if device_id in this_user_devices:
                    if device_id not in curr_user.devices_values:
                        curr_user.devices_values[device_id] = {}
                    for elem in add[device_id]:
                        curr_user.devices_values[device_id][elem] = add[device_id][elem]
                else:
                    logging.error("Incorrect device_id {0}. Only current user devices are allowed.".format(device_id))
            curr_user.devices_version += 1
            curr_user.put()


class DeleteValues:

    @staticmethod
    def delete(object, delete):
        to_delete = json.loads(delete)
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

    class Device(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(DeleteValues.Device, self).__init__(*args, **kwargs)

        def post(self):
            DeleteValues.delete(self.device_key, self.request.get("json"))

    class Devices(AuthorizedAPIRequestHandler):

        def __init__(self, *args, **kwargs):
            super(DeleteValues.Devices, self).__init__(*args, **kwargs)

        def post(self, *args, **kwargs):
            to_delete = json.loads(self.request.get("json"))
            if self.user_key != self.device_key:
                curr_user = self.user_key.get()
                this_user_devices = [device.get().device_id for device in curr_user.devices]
                if curr_user is None:
                    self.error(403)
                for device_id in to_delete:
                    if device_id in this_user_devices:
                        if device_id in curr_user.devices_values:
                            for elem in to_delete[device_id]:
                                if elem in curr_user.devices_values[device_id]:
                                    del curr_user.devices_values[device_id][elem]
                    else:
                        logging.error("Incorrect device_id {0}. Only current user devices are allowed.".format(device_id))
                curr_user.devices_version += 1
                curr_user.put()
            else:
                logging.error("No User")


class GetLastUserVersion(AuthorizedAPIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GetLastUserVersion, self).__init__(*args, **kwargs)

    def get(self):
        self.response.write(self.user_key.get().version)


class GetLastDeviceVersion(AuthorizedAPIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GetLastDeviceVersion, self).__init__(*args, **kwargs)

    def get(self):
        self.response.write(self.device_key.get().version)


class GetLastDevicesVersion(AuthorizedAPIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GetLastDevicesVersion, self).__init__(*args, **kwargs)

    def get(self):
        self.response.write(self.user_key.get().devices_version)