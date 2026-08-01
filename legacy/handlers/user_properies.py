__author__ = 'ivan'
import json
import logging
from handlers import AuthorizedAPIRequestHandler


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
            add = json.loads(self.request.get("json"))
            device_id = self.device_id
            if device_id not in curr_user.devices_values:
                curr_user.devices_values[device_id] = {}
            for elem in add:
                curr_user.devices_values[device_id][elem] = add[elem]

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
                if curr_user is None:
                    self.error(403)
                device_id = self.device_id
                if device_id in curr_user.devices_values:
                    for elem in to_delete:
                        if elem in curr_user.devices_values[device_id]:
                            del curr_user.devices_values[device_id][elem]

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