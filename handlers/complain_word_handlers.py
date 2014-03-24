import constants

__author__ = 'ivan'

import json

from google.appengine.ext import ndb
from google.appengine.api import users

from objects.complained_word import ComplainedWord
from environment import JINJA_ENVIRONMENT
from objects.global_dictionary_word import GlobalDictionaryWord
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from handlers.base_handlers.api_request_handlers import AuthorizedAPIRequestHandler


class ComplainWordHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ComplainWordHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        complained_word_json_list = \
            json.loads(self.request.get(constants.get_title))
        for current_word_json in complained_word_json_list:
            current_word = ComplainedWord(device=self.device_key,
                                          word=current_word_json[constants.complained_word],
                                          reason=current_word_json[constants.reason])
            if constants.word_to_replace in current_word_json:
                current_word.replacement_word = \
                    current_word_json[constants.word_to_replace]
            current_word.put()


class ShowComplainedWords(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ShowComplainedWords, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/complained_words.html')
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
        deleted_word = self.request.get(constants.deleted_word_name)
        ndb.delete_multi(ComplainedWord.query(ComplainedWord.word == deleted_word).fetch(keys_only=True))
        self.redirect("/admin/complain/list")


class DeleteFromGlobalDictionaryHandler(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteFromGlobalDictionaryHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        data = self.request.get(constants.complained_word)
        word = GlobalDictionaryWord.get_by_id(data)
        if word is not None:
            if word.tags.find("-deleted") != -1:
                word.tags += "-deleted"
            word.put()
        ndb.delete_multi(ComplainedWord.query(ComplainedWord.word == data).fetch(keys_only=True))
        self.redirect("/admin/complain/list")



