__author__ = 'Ivan'
from google.appengine.api import channel
import uuid
import webapp2
from google.appengine.ext import ndb

class NotificationChannel(ndb.Model):
    channel_id = ndb.StringProperty()
    channel_token = ndb.StringProperty()

class MakeChannelHandler(webapp2.RequestHandler):

    def __init__(self, *args, **kwargs):
        super(MakeChannelHandler, self).__init__(*args, **kwargs)

    def post(self):
        current_channel = ndb.Key(NotificationChannel, "notifications").get()
        channel_id = "notifications"
        channel_token = channel.create_channel(channel_id, 24 * 60) #The number of minutes for which the returned token will be valid
        if current_channel is None:
            NotificationChannel(channel_id=channel_id, channel_token=channel_token, id="notifications").put()
        else:
            current_channel.channel_id, current_channel.channel_token = channel_id, channel_token
            current_channel.put()


class NotificationHandler(webapp2.RequestHandler):

    def __init__(self, *args, **kwargs):
        super(NotificationHandler, self).__init__(*args, **kwargs)

    def post(self):
        current_channel = ndb.Key(NotificationChannel, "notifications").get()
        message = self.request.get("message")
        channel.send_message(current_channel.channel_id, message)

class NotificationShow(webapp2.RequestHandler):

    def __init__(self, *args, **kwargs):
        super(NotificationShow, self).__init__(*args, **kwargs)

    def get(self):
        curr_channel = ndb.Key(NotificationChannel, "notifications").get()
        self.draw_page('note_test',token=curr_channel.token if curr_channel else None)