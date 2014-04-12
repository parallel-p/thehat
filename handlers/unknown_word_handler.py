from google.appengine.ext import ndb
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord

__author__ = 'ivan'

from objects.unknown_word import UnknownWord


class page_word():

    def __init__(self, x, cnt):
        self.times_used = x.times_used
        self.ignored = x.ignored
        self.word = x.word
        self.id = cnt


class GetWordPageHandler(AdminRequestHandler):

    def __init(self, *args, **kwargs):
        super(GetWordPageHandler, self).__init__(*args, **kwargs)

    def get(self):
        self.response.headers.add_header('Access-Control-Allow-Origin', '*')
        words = [page_word(value, index) for index, value in enumerate(UnknownWord.query().order(-UnknownWord.times_used).filter(UnknownWord.ignored==False).fetch())]
        self.draw_page('unknown_word_page', word_list=words, quantity=len(words))


class IgnoreWordHanler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(IgnoreWordHanler, self).__init__(*args, **kwargs)

    def post(self):
        word = self.request.get("word")
        in_base = ndb.Key(UnknownWord, word).get()
        in_base.ignored = True
        in_base.put()


class AddWordHanler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AddWordHanler, self).__init__(*args, **kwargs)

    def post(self):
        word = self.request.get("word")
        GlobalDictionaryWord(word=word, cnt=0, tags="", id=word).put()
        ndb.Key(UnknownWord, word).get().key.delete()




