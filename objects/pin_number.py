__author__ = 'nikolay'

from google.appengine.ext import ndb
import time
import random


class PinNumber(ndb.Model):
    rand = ndb.IntegerProperty(indexed=False)
    expires = ndb.IntegerProperty()
    used = ndb.BooleanProperty()
    data = ndb.StringProperty(indexed=False)

    @staticmethod
    def generate(data=None, lifetime=30*60):
        obj = (PinNumber.query(PinNumber.used == False).get()
               or PinNumber.query(PinNumber.expires < int(PinNumber.time())).get()
               or PinNumber())
        obj.data = data
        obj.expires = int(PinNumber.time()) + lifetime
        obj.rand = random.randint(0, 9999)
        obj.used = True
        obj.put()
        return str(obj)

    @staticmethod
    def retrive(pin, data=None, remove=False):
        if not pin.isdigit():
            return None
        key = int(pin[:7:2]+pin[8:])
        rand = int(pin[1:8:2])
        key = ndb.Key(PinNumber, key)
        pin_number = key.get()
        if pin_number is None:
            return None
        if rand != pin_number.rand:
            return None
        if data is not None:
            if data != pin_number.data:
                return None
            if remove:
                del pin_number
        return pin_number

    def free(self):
        self.used = False
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




