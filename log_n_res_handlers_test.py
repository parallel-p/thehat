import unittest
import webapp2
import main
import json

SOME_RES = '{"some_results"}'


class TestResults(unittest.TestCase):
    def test_upload_n_load_results(self):
        request = webapp2.Request.blank('/179/upload_results/1', None, None, {"results": SOME_RES})
        request.method = 'GET'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        request = webapp2.Request.blank('/179/get_results/1')
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.body, SOME_RES)

    #def test_empty_post(self):
    #    request = webapp2.Request.blank('')
    #    request.method = 'POST'
    #    response = request.get_response(main.app)
    #    self.assertEqual(response.status_int, 200)