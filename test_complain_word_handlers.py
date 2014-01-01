__author__ = 'ivan'
import webtest
import unittest2
import webapp2

from complain_word_handlers import ComplainWordHandler


class ComplainWordHandlerTest(unittest2.TestCase):
    def setUp(self):
        routes = [
            (r'/complain/(\w+)/(\w+)/(0|1|2|3|4/)/(\w+)?', ComplainWordHandler)
        ]
        application = webapp2.WSGIApplication(routes, debug=True)
        self.testapp = webtest.TestApp(application)

    def test_post(self):
        response = self.testapp.post(r'/complain/123/vasya/1/aaa')
        self.assertEqual(response.status_int, 200)


if __name__ == '__main__':
    unittest2.main()
