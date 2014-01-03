__author__ = 'ivan'

import json
from all_handler import AllHandler
from objects.global_dictionary_word import GlobalDictionaryWord


class GlobalDictionaryWordHandler(AllHandler):
    @staticmethod
    def make_json():
        words = []
        for word in GlobalDictionaryWord.all():
            to_json = {"word": word.word, "E": word.E, "D": word.D}
            words.append(to_json)
        return json.dumps(words)

    def get(self, **kwargs):
        super(GlobalDictionaryWordHandler, self).set_device_id(**kwargs)
        self.response.write(GlobalDictionaryWordHandler.make_json())

