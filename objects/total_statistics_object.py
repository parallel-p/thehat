__author__ = 'ivan'

from google.appengine.ext import ndb


class TotalStatisticsObject(ndb.Model):

    count_for_date_json = ndb.JsonProperty()
    time_for_date_json = ndb.JsonProperty()
    average_time_json = ndb.JsonProperty()