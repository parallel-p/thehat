import unittest
import main
import dictionaries_packages_handlers
import webapp2


class PackagesHandlersTest(unittest.TestCase):
    def test_get_streams_list_handler(self):
        request = webapp2.Request.blank(r'/a/streams')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_change_stream_state_handler(self):
        request = webapp2.Request.blank(r'/a/streams/stream1/to/true')
        request.method = 'POST';
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_get_packages_list_handler(self):
        request = webapp2.Request.blank(r'/a/streams/stream1')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def test_get_package_handler(self):
        request = webapp2.Request.blank(r'/a/streams/packages/package1')
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)


if __name__ == '__main__':
    unittest.main()

