__author__ = 'ivan'
import unittest2
import webapp2
from google.appengine.ext import testbed

import main


class IntegrationTest(unittest2.TestCase):
    @staticmethod
    def create_request(request_url, request_method, request_body=None):
        request = webapp2.Request.blank(request_url)
        request.method = request_method
        if request_body is not None:
            request.body = request_body
        return request

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
