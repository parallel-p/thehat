from google.appengine.ext import ndb
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord

__author__ = 'ivan'

from objects.unknown_word import UnknownWord


class GetWordPageHandler(AdminRequestHandler):
    def get(self):
        self.response.headers.add_header('Access-Control-Allow-Origin', '*')
        words = UnknownWord.query().order(-UnknownWord.times_used).filter(UnknownWord.ignored == False).fetch()
        self.draw_page('unknown_word_page', word_list=words)


def ignore_word(word):
    in_base = ndb.Key(UnknownWord, word).get()
    in_base.ignored = True
    in_base.put()


class IgnoreWordHanler(AdminRequestHandler):
    def post(self):
        word = self.request.get("word")
        ignore_word(word)


class AddWordHanler(AdminRequestHandler):
    def post(self):
        word = self.request.get("word")
        GlobalDictionaryWord(word=word, cnt=0, tags="", id=word).put()
        ignore_word(word)




