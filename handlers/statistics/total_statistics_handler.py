__author__ = 'ivan'

import webapp2

from environment import *
from handlers.base_handlers.web_request_handler import WebRequestHandler
from google.appengine.ext import ndb
import collections
import datetime


class TotalStatisticsHandler(WebRequestHandler):


    def __init__(self, *args, **kwargs):
        super(TotalStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        current_statistics_object = ndb.gql("SELECT * FROM TotalStatisticsObject").get()
        if current_statistics_object is None:
            self.response.write("no stat")
        else:
            a, b, c = [], [], []
            for i in sorted(current_statistics_object.count_for_date_json):
                a.append((datetime.datetime.fromtimestamp(int(i)).strftime('%Y-%m-%d'), current_statistics_object.count_for_date_json[i]))
            for i in sorted(current_statistics_object.time_for_date_json):
                b.append((datetime.datetime.fromtimestamp(int(i)).strftime('%Y-%m-%d'), current_statistics_object.time_for_date_json[i]))
            for i in sorted(current_statistics_object.average_time_json):
                c.append((datetime.datetime.fromtimestamp(int(i)).strftime('%Y-%m-%d'), current_statistics_object.average_time_json[i]))
            print(a, b, c)
            self.draw_page("statistics/total_statistic",
                           count_for_date=a
                           if current_statistics_object else {},
                           time_for_date=b
                           if current_statistics_object else {},
                           average_time=c
                           if current_statistics_object else {})

total_statistics_routes = [
    webapp2.Route('/statistics/total_statistics',
                  handler=TotalStatisticsHandler,
                  name="total statistics handler")
]