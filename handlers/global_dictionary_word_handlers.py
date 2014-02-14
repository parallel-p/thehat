import constants

__author__ = 'ivan'

import json

from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import ndb

from objects.global_dictionary_word import GlobalDictionaryWord
from objects.global_dictionary_version import GlobalDictionaryVersion
import constants.constants
from environment import *
from objects.GlobalDictionaryJSON import GlobalDictionaryJson
from base_handlers.api_request_handlers import APIRequestHandler
from base_handlers.admin_request_handler import AdminRequestHandler
import webapp2
import time


class dictionary_updater(webapp2.RequestHandler):
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

            in_base = ndb.Key(GlobalDictionaryWord, word).get()
            if in_base is not None:
                continue
            changed = True
            if len(splited) >= 2:
                E = float(splited[1])
            if len(splited) >= 3:
                D = float(splited[2])
            new_word = GlobalDictionaryWord(id=word, word=word, E=E, D=D, tags="")
            new_word.put()
        if changed:
            #TODO: i think we must date Json one or two times a day.
            time.sleep(1)
            GlobalDictionaryJson.update_json()

    @staticmethod
    def run_update(data):
        taskqueue.add(url='/json_updater', params={'data': data})


class GlobalDictionaryWordHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GlobalDictionaryWordHandler, self).__init__(*args, **kwargs)

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
