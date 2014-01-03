from google.appengine.ext import ndb


class UserStreams(ndb.Model):
    user_id = ndb.StringProperty()
    streams = ndb.StringProperty(repeated=True)
