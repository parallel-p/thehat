__author__ = 'nikolay'

from google.appengine.ext import ndb


class UserPin(ndb.Model):
    user = ndb.UserProperty()
    pin = ndb.StringProperty()
    time = ndb.IntegerProperty()


class DeviceUser(ndb.Model):
    device_id = ndb.StringProperty()
    user_id = ndb.StringProperty()


def get_user_by_device(device_id):
    device_user = DeviceUser.query(DeviceUser.device_id == device_id).get()
    if device_user is None:
        return 'device_%s' % device_id
    else:
        return device_user.user_id