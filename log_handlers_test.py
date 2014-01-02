import unittest
import webapp2
import main

ROUNDS_JSON = '''
{
    "rounds": [
        {
            "explain_player": "vasya",
            "guess_player": "petya"
            "word": {
                "text": "hat"
                "state" : 1
                "time_sec": 4.3
                "tries": 2
            }
        },
        {
            "explain_player": "petya",
            "guess_player": "masha"
            "word": {
                "text": "hat"
                "state" : 2
                "time_sec": None
                "tries": None
            }
        }
    ]
}
'''


class TestResults(unittest.TestCase):
    def test_send_rounds(self):
        request = webapp2.Request.blank('/send_round/1', None, None, {"rounds": ROUNDS_JSON})
        request.method = 'POST'
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        #self.assertEqual(len(), 2)

    #def test_empty_post(self):
    #    request = webapp2.Request.blank('')
    #    request.method = 'POST'
    #    response = request.get_response(main.app)
    #    self.assertEqual(response.status_int, 200)