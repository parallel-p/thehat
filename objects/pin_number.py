__author__ = 'nikolay'

from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel
import time
import random


class PinNumberData(polymodel.PolyModel):
    pass


class PinNumber(ndb.Model):
    rand = ndb.IntegerProperty(indexed=False)
    expires = ndb.IntegerProperty()
    used = ndb.BooleanProperty()
    data_key = ndb.StringProperty(indexed=False)
    data = ndb.StringProperty(indexed=False)

    @staticmethod
    def generate(key, data="", lifetime=30 * 60):
        obj = (PinNumber.query(PinNumber.used == False).get()
               or PinNumber.query(PinNumber.expires < int(PinNumber.time())).get()
               or PinNumber())
        obj.data_key = key
        obj.data = data
        obj.expires = int(PinNumber.time()) + lifetime
        obj.rand = random.randint(0, 9999)
        obj.used = True
        obj.put()
        return str(obj)

    @staticmethod
    def retrive(pin, key=None, free=False):
        if not pin.isdigit():
            return None
        entity_key = int(pin[:7:2] + pin[8:])
        rand = int(pin[1:8:2])
        entity_key = ndb.Key(PinNumber, entity_key)
        pin_number = entity_key.get()
        if pin_number is None:
            return None
        if rand != pin_number.rand:
            return None
        if key is not None:
            if key != pin_number.data_key:
                return None
            if free:
                pin_number.free()
        return pin_number

    def free(self):
        self.used = False
        ndb.delete_multi(PinNumberData.query(ancestor=self.key).fetch(keys_only=True))
        self.put()

    def __str__(self):
        key = "{0:0>4}".format(self.key.id())
        rand = "{0:0>4}".format(self.rand)
        parts = []
        for i in xrange(4):
            parts.append(key[i])
            parts.append(rand[i])
        parts.append(key[4:])
        return ''.join(parts)

    @staticmethod
    def time():
        return time.time()




