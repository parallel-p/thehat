import unittest
import results_handlers

class TestResults(unittest.TestCase):
    def setUp(self):
        pass

    def test_empty_get(self):
        handler = results_handlers.GetResultsHandler()
        handler.get(1)

    def test_empty_post(self):
        handler = results_handlers.PostResultsHandler()
        handler.post(1)