from google.appengine.ext import ndb


class UserStreams(ndb.Model):
    streams = ndb.StringProperty(repeated=True)
