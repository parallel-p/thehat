__author__ = 'ivan'

from generic_handler import GenericHandler
from objects.user_devices import get_user_by_device


class APIRequestHandler(GenericHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)


class AuthorizedAPIRequestHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)
        self.device_id = None
        self.device_key = None
        self.user_key = None

    def authorizate(self, **kwargs):
        self.device_id = kwargs.get('device_id', None)
        if self.device_id is None:
            self.response.headers.add("WWW-Authenticate", "device-id")
            self.abort(401)
        self.device_key, self.user_key = get_user_by_device(self.device_id)



