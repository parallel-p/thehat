__author__ = 'nikolay'
from google.appengine.ext.ndb import IntegerProperty


class EnumProperty(IntegerProperty):
    def __init__(self, enum, **kwargs):
        super(EnumProperty, self).__init__(**kwargs)
        i = 0
        self.enum = {}
        self.values = []
        for k, v in enum.items():
            self.enum[k] = i
            self.enum[v] = i
            self.values.append(v)
            i += 1

    def __getattr__(self, item):
        return self.enum[item]

    def _validate(self, value):
        if not isinstance(value, str):
            raise TypeError('expected an string, got %s' % repr(value))
        if not value in self.enum:
            raise ValueError('unknown enum key')
        return self.values[self.enum[value]]

    def _to_base_type(self, value):
        return self.enum[value]

    def _from_base_type(self, value):
        return self.values[value]