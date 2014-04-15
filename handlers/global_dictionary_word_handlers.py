__author__ = 'ivan'

import time
import json

from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from objects.global_dictionary_word import GlobalDictionaryWord
from objects.GlobalDictionaryJSON import GlobalDictionaryJson
from handlers.base_handlers.api_request_handlers import APIRequestHandler
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler


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

    def get(self):
        self.draw_page('addwordsscreen')


class TaskQueueAddWords(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(TaskQueueAddWords, self).__init__(*args, **kwargs)

    def post(self):
        new_words = json.loads(self.request.get("json"))
        for word in new_words:
            GlobalDictionaryWord(id=word, word=word, E=50.0, D=50.0/3, tags="").put()


class TaskQueueUpdateJson(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(TaskQueueUpdateJson, self).__init__(*args, **kwargs)

    def post(self):
        timestamp = int(self.request.get("timestamp"))
        max_timestamp = 0
        word_list = []
        for word in GlobalDictionaryWord.query().fetch():
            word_time = int(time.mktime(word.timestamp.timetuple()) * 1000)
            if word_time > timestamp:
                max_timestamp = max(max_timestamp, word_time)
                word_list.append({"word": word.word, "E": word.E, "D": word.D, "U": word.used_times, "tags": word.tags})
        if word_list:
            GlobalDictionaryJson(json=json.dumps(word_list), timestamp=max_timestamp).put()


class UpdateAllJsonsHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateAllJsonsHandler, self).__init__(*args, **kwargs)

    def post(self):
        for this_json in ndb.gql("SELECT timestamp FROM GlobalDictionaryJson"):
            this_json.key.delete()
        taskqueue.add(url='/internal/global_dictionary/update_json/task_queue', params={"timestamp": 0})


class UpdateJsonHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateJsonHandler, self).__init__(*args, **kwargs)

    def post(self):
        max_timestamp = 0
        for json in ndb.gql("SELECT timestamp FROM GlobalDictionaryJson"):
            if json.timestamp > max_timestamp:
                max_timestamp = json.timestamp
        taskqueue.add(url='/internal/global_dictionary/update_json/task_queue', params={"timestamp": max_timestamp})


class DeleteDictionary(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(DeleteDictionary, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        taskqueue.add(url='/internal/global_dictionary/delete/task_queue')


class DeleteDictionaryTaskQueue(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(DeleteDictionaryTaskQueue, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        for word in ndb.gql("SELECT word FROM GlobalDictionaryWord").fetch():
            word.key.delete()
        for json in ndb.gql("SELECT timestamp FROM GlobalDictionaryJson").fetch():
            json.key.delete()


class GlobalDictionaryGetWordsHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GlobalDictionaryGetWordsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        device_timestamp = int(kwargs.get("timestamp"))
        max_timestamp = 0
        response_json = {"words": []}
        for diff_json in ndb.gql("SELECT timestamp FROM GlobalDictionaryJson "
                                 "ORDER BY timestamp"):
            max_timestamp = max(max_timestamp, diff_json.timestamp)
            if diff_json.timestamp > device_timestamp:
                for res_json in ndb.gql("SELECT * FROM GlobalDictionaryJson "
                                        "WHERE timestamp = {0} "
                                        "ORDER BY timestamp".format(diff_json.timestamp)):
                    to_add = json.loads(res_json.json)
                    response_json["words"].extend(to_add)
        response_json["timestamp"] = max_timestamp
        self.response.write(json.dumps(response_json))



