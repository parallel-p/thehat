__author__ = 'ivan'

from google.appengine.ext import db
from objects.global_dictionary_word import GlobalDictionaryWord
from objects.global_dictionary_version import GlobalDictionaryVersion
import constants.constants
import json
import time


class GlobalDictionaryJson(db.Model):
    json = db.TextProperty()

    @staticmethod
    def get_json():
        json = GlobalDictionaryJson.get_by_key_name('json')
        return "{}" if json is None else json.json

    @staticmethod
    def make_json():
        words = []
        for word in GlobalDictionaryWord.all():
            to_json = {constants.constants.global_dict_word: word.word,
                       constants.constants.Expectation: float(word.E),
                       constants.constants.Dispersion: float(word.D),
                       constants.constants.Tags: word.tags}
            words.append(to_json)
        return json.dumps(words)

    @staticmethod
    def update_json():
        new_json = GlobalDictionaryJson.make_json()
        server_json = GlobalDictionaryJson.get_by_key_name('json')
        if server_json is None:
            server_json = GlobalDictionaryJson(key_name='json', json=new_json)
        else:
            server_json.json = new_json
        server_json.put()
        GlobalDictionaryVersion.update_version()