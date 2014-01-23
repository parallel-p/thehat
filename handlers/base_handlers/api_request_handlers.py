__author__ = 'ivan'

from all_handler import AllHandler


class APIRequestHandler(AllHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)
        self.device_id = None

    def get_device_id(self, **kwargs):
        self.device_id = kwargs.get('device_id', None)



