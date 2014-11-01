from handlers import AdminRequestHandler, APIRequestHandler, ServiceRequestHandler

import datetime, time
import json

import lib.cloudstorage as gcs
from google.appengine.api import app_identity
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from objects.global_dictionary import GlobalDictionaryWord


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


class TaskQueueUpdateDictionary(ServiceRequestHandler):
    def post(self):
        last_update = datetime.datetime.fromtimestamp(int(self.request.get("timestamp")))
        word_list = []
        for word in GlobalDictionaryWord.query(GlobalDictionaryWord.timestamp > last_update).fetch():
            word_list.append({"word": word.word, "E": word.E, "D": word.D, "U": word.used_times, "tags": word.tags})
        if word_list:
            bucket_name = app_identity.get_default_gcs_bucket_name()
            now = int(time.time())
            data_object = {"created": now, "words": word_list}
            f = gcs.open("/{}/dictionary_update/{:0>11}".format(bucket_name, now), "w", "application/json")
            json.dump(data_object, f)
            f.close()


class RegenerateDictionaryUpdate(AdminRequestHandler):
    def post(self):
        bucket_name = app_identity.get_default_gcs_bucket_name() 
        import logging
        logging.debug("bucket name is: {}".format(bucket_name))
        for el in gcs.listbucket("/{}/dictionary_update".format(bucket_name)):
            gcs.delete(el.filename)
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
    def get(self, *args, **kwargs):
        import shutil
        last_update = kwargs.get("timestamp")
        self.response.write("[")
        bucket_name = app_identity.get_default_gcs_bucket_name()
        not_first = False
        for el in gcs.listbucket("/{}/dictionary_update".format(bucket_name), marker="/{}/dictionary_update/{}".format(bucket_name, last_update)):
            if not_first:
                self.response.write(",")
            f = gcs.open(el.filename)
            shutil.copyfileobj(f, self.response)
            f.close()
            not_first = True
        self.response.write("]")
