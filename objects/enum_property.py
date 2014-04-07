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
            self.values.append(v)
            i += 1

    def __getattr__(self, item):
        return self.enum[item]

    def _validate(self, value):
        if isinstance(value, str):
            if not value in self.enum:
                raise ValueError('unknown enum key')
            return self.enum[value]
        elif not isinstance(value, int):
            raise TypeError('expected an integer, got %s' % repr(value))
        elif value < 0 or value > len(self.values):
            raise ValueError('value is outside bounds')
        else:
            return value

    def __str__(self):
        return self.values[int(self)]