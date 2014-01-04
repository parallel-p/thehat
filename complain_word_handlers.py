__author__ = 'ivan'

import json

from google.appengine.ext import db
import webapp2

from all_handler import AllHandler
from objects.complained_word import ComplainedWord
from environment import JINJA_ENVIRONMENT
import constants.constants
from objects.global_dictionary_word import GlobalDictionaryWord


class ComplainWordHandler(AllHandler):
    def post(self, **kwargs):
        super(ComplainWordHandler, self).set_device_id(**kwargs)
        complained_word_json_list = \
            json.loads(self.request.get(constants.constants.get_title))
        for current_word_json in complained_word_json_list:
            current_word = ComplainedWord(device_id=self.device_id,
                                          word=current_word_json[constants.constants.complained_word],
                                          reason=current_word_json[constants.constants.reason])
            if constants.constants.word_to_replace in current_word_json:
                current_word.replacement_word = \
                    current_word_json[constants.constants.word_to_replace]
            current_word.put()


class ShowComplainedWords(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/complained_words.html')
        cnt = 0
        render_data = {constants.constants.render_data_name: []}
        for word in ComplainedWord.all():
            word_render = word
            word_render.cnt = cnt
            if word.replacement_word is None:
                word_render.replacement_word = ''
            render_data[constants.constants.render_data_name].append(word_render)
            cnt += 1
        self.response.write(template.render(render_data))


class DeleteComplainedWords(webapp2.RequestHandler):
    def post(self):
        for word in ComplainedWord.all():
            db.delete(word)
        self.redirect(constants.constants.show_complained_url)


class DeleteComplainedWord(webapp2.RequestHandler):
    def post(self):
        deleted_word = self.request.get(constants.constants.deleted_word_name)
        for word in ComplainedWord.all():
            if word.word == deleted_word:
                db.delete(word)
        self.redirect(constants.constants.show_complained_url)

class DeleteFromGlobalDictionaryHandler(webapp2.RequestHandler):

    def post(self):
        data = self.request.get(constants.constants.complained_word)
        word = GlobalDictionaryWord.get_by_key_name(data)
        if word is not None:
            word.tags+=" deleted "
            word.put()
        self.redirect(constants.constants.show_complained_url)




