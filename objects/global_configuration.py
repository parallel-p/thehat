from google.appengine.ext import ndb

class GlobalConfiguration(ndb.Model):
    @staticmethod
    def load():
        return ndb.Key(GlobalConfiguration, 'singleton').get() or GlobalConfiguration(id='singleton')
