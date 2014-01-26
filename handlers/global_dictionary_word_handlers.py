__author__ = 'ivan'

import json

from google.appengine.api import taskqueue
from google.appengine.api import users

from objects.global_dictionary_word import GlobalDictionaryWord
from objects.global_dictionary_version import GlobalDictionaryVersion
import constants.constants
from environment import *
from objects.GlobalDictionaryJSON import GlobalDictionaryJson
from base_handlers.api_request_handlers import APIRequestHandler
from base_handlers.admin_request_handler import AdminRequestHandler


class dictionary_updater(AdminRequestHandler):
    def post(self):
        str_data = self.request.get('data')
        data = str_data.split('\n') if str_data.find('\n') != -1 else [str_data, ]
        changed = False
        for i in data:
            word_info = i.strip()
            splited, E, D = [word_info, ], 50.0, float(50.0 / 3)
            if word_info.count(' ') != 0:
                splited = word_info.split()
            word = splited[0]

            in_base = GlobalDictionaryWord.get_by_key_name(word)
            if in_base is not None:
                continue
            changed = True
            if len(splited) >= 2:
                E = float(splited[1])
            if len(splited) >= 3:
                D = float(splited[2])
            new_word = GlobalDictionaryWord(key_name=word, word=word, E=E, D=D, tags="")
            new_word.put()
        if changed:
            server_json = GlobalDictionaryJson.get_by_key_name('json')
            new_json = GlobalDictionaryWordHandler.make_json()
            if server_json is None:
                server_json = GlobalDictionaryJson(key_name='json', json=new_json)
            else:
                server_json.json = new_json
            server_json.put()
            GlobalDictionaryVersion.update_version()

    @staticmethod
    def run_update(data):
        taskqueue.add(url='/json_updater', params={'data': data})


class GlobalDictionaryWordHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GlobalDictionaryWordHandler, self).__init__(*args, **kwargs)

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

    def get(self, **kwargs):
        super(GlobalDictionaryWordHandler, self).get_device_id(**kwargs)
        device_version = int(kwargs.get("version"))
        if device_version == GlobalDictionaryVersion.get_server_version():
            self.response.write("{}")
        else:
            self.response.write(GlobalDictionaryJson.get_json())


class GlobalWordEditor(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(AdminRequestHandler, self).__init__(*args, **kwargs)

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/addwordsscreen.html')
        if users.get_current_user():
            self.response.write(template.render(
                {"logout_link": users.create_logout_url('/')}))
        else:
            self.response.write(template.render({"login_link": users.create_login_url('/')}))

    def post(self):
        str_data = self.request.get('text').strip()
        dictionary_updater.run_update(str_data)
        self.redirect('/edit_words')
