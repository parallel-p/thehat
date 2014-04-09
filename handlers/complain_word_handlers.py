__author__ = 'ivan'

import json

from google.appengine.ext import ndb

from objects.global_dictionary_word import GlobalDictionaryWord
from objects.complained_word import ComplainedWord
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from handlers.base_handlers.api_request_handlers import AuthorizedAPIRequestHandler


class ComplainWordHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ComplainWordHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        complained_word_json_list = \
            json.loads(self.request.get("json"))
        for current_word_json in complained_word_json_list:
            current_word = ComplainedWord(device=self.device_key,
                                          word=current_word_json["word"],
                                          reason=current_word_json["reason"])
            if "replace_word" in current_word_json:
                current_word.replacement_word = \
                    current_word_json["replace_word"]
            current_word.put()


class ShowComplainedWords(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ShowComplainedWords, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        cnt = 0
        words = []
        for word in ComplainedWord.query():
            word_render = word
            word_render.cnt = cnt
            if word.replacement_word is None:
                word_render.replacement_word = ''
            words.append(word_render)
            cnt += 1
        self.draw_page('complained_words', quantity=len(words), words=words)


class DeleteComplainedWords(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteComplainedWords, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        ndb.delete_multi(ComplainedWord.query().fetch(keys_only=True))
        self.redirect("/admin/complain/list")


class DeleteComplainedWord(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteComplainedWord, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        deleted_word = self.request.get("word")
        ndb.delete_multi(ComplainedWord.query(ComplainedWord.word == deleted_word).fetch(keys_only=True))


class PostponeComplainedWord(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(PostponeComplainedWord, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        deleted_word = self.request.get("word")
        print(deleted_word)
        ndb.delete_multi(ComplainedWord.query(ComplainedWord.word == deleted_word).fetch(offset=1, keys_only=True))

class DeleteFromGlobalDictionaryHandler(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteFromGlobalDictionaryHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        data = self.request.get("word")
        word = ndb.Key(GlobalDictionaryWord, data).get()
        if word is not None:
            if word.tags.find("-deleted") == -1:
                word.tags += "-deleted"
            word.put()
        ndb.delete_multi(ComplainedWord.query(ComplainedWord.word == data).fetch(keys_only=True))



