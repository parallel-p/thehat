__author__ = 'ivan'

import time

from google.appengine.api import taskqueue
from google.appengine.api import users
import webapp2
import json

from objects.global_dictionary_word import GlobalDictionaryWord
from environment import *
from objects.GlobalDictionaryJSON import GlobalDictionaryJson
from google.appengine.ext import ndb
from handlers.base_handlers.api_request_handlers import APIRequestHandler
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler


def make_timestamp():
    return int(1000 * time.time())

StrategyTypeChooseConstant = 200


class WordsAddHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WordsAddHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        words = json.loads(self.request.get("json"))
        to_add = []
        if len(words) > StrategyTypeChooseConstant:
            server = set([word.word for word in ndb.gql(u"SELECT word FROM GlobalDictionaryWord")])
            for i in words:
                if not i in server:
                    to_add.append(i)
        else:
            for word in words:
                in_base = ndb.Key(GlobalDictionaryWord, word).get()
                if in_base is None:
                    to_add.append(word)
        taskqueue.add(url='/internal/global_dictionary/add_words/task_queue', params={"json": json.dumps(to_add)})


class TaskQueueAddWords(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(TaskQueueAddWords, self).__init__(*args, **kwargs)

    def post(self):
        new_words = json.loads(self.request.get("json"))
        for word in new_words:
            GlobalDictionaryWord(id=word, word=word, E=50.0, D=50.0/3, tags="",
                                 timestamp=make_timestamp()).put()


class TaskQueueUpdateJson(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(TaskQueueUpdateJson, self).__init__(*args, **kwargs)

    def post(self):
        timestamp = int(self.request.get("timestamp"))
        max_timestamp = 0
        word_list = []
        for word in ndb.gql(u"SELECT word, timestamp FROM GlobalDictionaryWord"):
            if word.timestamp > timestamp:
                max_timestamp = max(max_timestamp, word.timestamp)
                downloaded_word = ndb.gql(u"SELECT * from GlobalDictionaryWord WHERE word = '{0}'".format(word.word)).get()
                word_list.append({"word": word.word, "tags": downloaded_word.tags})
        GlobalDictionaryJson(json=json.dumps(word_list), timestamp=max_timestamp).put()


class UpdateJsonHandler(APIRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateJsonHandler, self).__init__(*args, **kwargs)

    def post(self):
        max_timestamp = 0
        for json in ndb.gql("SELECT timestamp FROM GlobalDictionaryJson"):
            if json.timestamp > max_timestamp:
                max_timestamp = json.timestamp
        taskqueue.add(url='/internal/global_dictionary/update_json/task_queue', params={"timestamp":max_timestamp})


class GlobalDictionaryGetWordsHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GlobalDictionaryGetWordsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        device_timestamp = int(kwargs.get("timestamp"))
        max_timestamp = 0
        response_json = {"words":[]}
        for diff_json in ndb.gql("SELECT timestamp FROM GlobalDictionaryJson "
                                 "ORDER BY timestamp"):
            if diff_json.timestamp > device_timestamp:
                max_timestamp = max(max_timestamp, diff_json.timestamp)
                for res_json in ndb.gql("SELECT * FROM GlobalDictionaryJson "
                                        "WHERE timestamp = {0} "
                                        "ORDER BY timestamp".format(diff_json.timestamp)):
                    to_add = json.loads(res_json.json)
                    response_json["words"].extend(to_add)
        response_json["timestamp"] = max_timestamp
        self.response.write(json.dumps(response_json))


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


global_dictionary_word_routes = [
    webapp2.Route(r'/admin/global_dictionary/add_words',
                  handler=WordsAddHandler,
                  name='add words to global'),
    webapp2.Route(r'/internal/global_dictionary/add_words/task_queue',
                  handler=TaskQueueAddWords,
                  name='add words to global task queue'),
    webapp2.Route(r'/internal/global_dictionary/update_json/task_queue',
                  handler=TaskQueueUpdateJson,
                  name='update json task queue'),
        webapp2.Route(r'/admin/global_dictionary/update_json',
                  handler=UpdateJsonHandler,
                  name='update json'),
        webapp2.Route(r'/api/global_dictionary/get_words/<timestamp:[-\d]+>',
                  handler=GlobalDictionaryGetWordsHandler,
                  name='get words')
]