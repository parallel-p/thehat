from handlers import AdminRequestHandler

__author__ = 'nikolay'
from objects.global_dictionary_word import WordLookup
import json


class AddLookups(AdminRequestHandler):
    def post(self):
        words = json.loads(self.request.get("json"))
        for word in words:
            WordLookup(id=word["lookup"],
                       proper_word=word["word"]).put()
