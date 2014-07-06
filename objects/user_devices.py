__author__ = 'nikolay'

from google.appengine.ext import ndb


class User(ndb.Model):
    user_id = ndb.StringProperty()
    user_object = ndb.UserProperty()
    devices = ndb.KeyProperty(repeated=True)
    values = ndb.JsonProperty(default={})
    version = ndb.IntegerProperty(default=0)
    devices_values = ndb.JsonProperty(default={})
    devices_version = ndb.IntegerProperty(default=0)
    localization = ndb.StringProperty(default='ru_RU')


class Device(ndb.Model):
    device_id = ndb.StringProperty()
    values = ndb.JsonProperty(default={})
    version = ndb.IntegerProperty(default=0)


class OwnedModel(ndb.Model):
    owner = ndb.KeyProperty()

    @classmethod
    def query(cls, user, *args, **kwargs):
        if not isinstance(user, ndb.Key):
            raise TypeError()
        if user.kind() == 'User':
            devices = user.get().devices[:]
            devices.append(user)
            filt = cls.owner.IN(devices)
        elif user.kind() == 'Device':
            filt = cls.owner == user
        else:
            raise ValueError()
        return super(OwnedModel, cls).query(filt, *args, **kwargs)


def get_device(device_id):
    return Device.query(Device.device_id == device_id).get(keys_only=True) or Device(device_id=device_id).put()


def get_user(user_object):
    return User.query(User.user_id == user_object.user_id()).get(keys_only=True) or User(user_id=user_object.user_id(),
                                                                                         user_object=user_object).put()


def get_device_and_user(device_id):
    device = get_device(device_id)
    user = User.query(User.devices == device).get(keys_only=True)
    if user is None:
        return device, device
    else:
        return device, user