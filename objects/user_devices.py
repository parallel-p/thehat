__author__ = 'nikolay'

from google.appengine.ext import ndb


class User(ndb.Model):
    user = ndb.UserProperty()


class Device(ndb.Model):
    device_id = ndb.StringProperty()


def get_device(device_id):
    return Device.query(Device.device_id == device_id).get(keys_only=True) or Device(device_id=device_id).put()


def get_user_by_device(device_id):
    device = get_device(device_id)
    if device.parent() is None:
        return device, device
    else:
        return device, device.parent()