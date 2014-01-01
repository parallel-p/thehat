import unittest
import webapp2
import main


class TestResults(unittest.TestCase):
    def setUp(self):
        self.request = webapp2.Request.blank(r'/results/1')

    def test_empty_get(self):
        response = self.request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_empty_post(self):
        self.request.method = 'POST'
        response = self.request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
