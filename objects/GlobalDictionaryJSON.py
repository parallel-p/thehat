__author__ = 'ivan'

from google.appengine.ext import db

class GlobalDictionaryJson(db.Model):
    json = db.TextProperty()

    @staticmethod
    def get_json():
        json = GlobalDictionaryJson.get_by_key_name('json')
        return "{}" if json is None else json.json