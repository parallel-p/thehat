from google.appengine.ext import ndb

class GlobalConfiguration(ndb.Model):
    dictionary_gcs_key = ndb.StringProperty()

    @staticmethod
    def load():
        return ndb.Key(GlobalConfiguration, 'singleton').get() or GlobalConfiguration(id='singleton')
