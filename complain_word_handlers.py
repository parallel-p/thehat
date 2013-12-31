__author__ = 'ivan'

import webapp2
from complained_word_list import ComplainedWordList
from complained_word import ComplainedWord


class ComplainWordHandler(webapp2.RequestHandler):
    def __init__(self):
        self.complained_words = ComplainedWordList()

    def post(self, *args):
        device_id, word, cause = args[0], args[1], args[2]
        self.complained_words.add(ComplainedWord(device_id, word, cause, None if len(args) == 3 else args[4]))
        self.response.write('post, ok')

    def get(self, *args):
        self.response.write('get, ok')
