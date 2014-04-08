__author__ = 'nikolay'
from objects.global_dictionary_word import WordLookup
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
import json


class AddLookups(AdminRequestHandler):
    def post(self):
        words = json.loads(self.request.get("json"))
        for word in words:
            WordLookup(id=word["lookup"], proper_word=word["word"]).put()