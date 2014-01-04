__author__ = 'ivan'

import json
import webapp2
from all_handler import AllHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from objects.global_dictionary_version import GlobalDictionaryVersion
import constants.constants
from environment import *


class GlobalDictionaryWordHandler(AllHandler):
    @staticmethod
    def make_json():
        words = []
        for word in GlobalDictionaryWord.all():
            to_json = {constants.constants.global_dict_word: word.word,
                       constants.constants.Expectation: word.E,
                       constants.constants.Dispersion: word.D,
                       constants.constants.Tags: word.tags}
            words.append(to_json)
        return json.dumps(words)

    def get(self, **kwargs):
        super(GlobalDictionaryWordHandler, self).set_device_id(**kwargs)
        device_version = int(kwargs.get("version"))

        if device_version == GlobalDictionaryVersion.get_server_version():
            self.response.write("{}")
        else:
            self.response.write(GlobalDictionaryWordHandler.make_json())


class GlobalWordEditor(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/addwordsscreen.html')
        self.response.write(template.render())

    def post(self):
        data = self.request.get('text').strip().split('\n')
        smth_changed = False
        for i in data:
            word_info = i.strip()
            splited, E, D = [word_info, ], 50, 50 / 3
            if word_info.count(' ') != 0:
                splited = word_info.split()
            word = splited[0]

            in_base = GlobalDictionaryWord.get_by_key_name(word)
            if in_base is not None:
                continue
            smth_changed = True
            if len(splited) >= 2:
                E = float(splited[1])
            if len(splited) >= 3:
                D = float(splited[2])
            new_word = GlobalDictionaryWord(key_name=word, word=word, E=E, D=D)
            new_word.put()
        if smth_changed:
            GlobalDictionaryVersion.update_version()





