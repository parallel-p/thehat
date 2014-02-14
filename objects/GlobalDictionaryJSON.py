__author__ = 'ivan'

from google.appengine.ext import db
from objects.global_dictionary_word import GlobalDictionaryWord
from objects.global_dictionary_version import GlobalDictionaryVersion
import constants
import json


class GlobalDictionaryJson(db.Model):
    json = db.TextProperty()

    @staticmethod
    def get_json():
        json = GlobalDictionaryJson.get_by_key_name('json')
        return "{}" if json is None else json.json

    @staticmethod
    def make_json():
        words = []
        for word in GlobalDictionaryWord.query().fetch():
            to_json = {constants.global_dict_word: word.word,
                       constants.Expectation: float(word.E),
                       constants.Dispersion: float(word.D),
                       constants.Tags: word.tags}
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