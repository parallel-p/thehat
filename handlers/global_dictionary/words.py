from handlers import AdminRequestHandler, APIRequestHandler, ServiceRequestHandler

import time
import json

import lib.cloudstorage as gcs
from google.appengine.api import app_identity
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from objects.global_dictionary import GlobalDictionaryWord
from objects.global_configuration import GlobalConfiguration


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


def get_gcs_filename(key):
    bucket_name = app_identity.get_default_gcs_bucket_name()
    return "/{}/dictionary/{}".format(bucket_name, key)

class GenerateDictionary(ServiceRequestHandler):
    def post(self):
        data_object = []
        key = str(int(time.time()))
        words = GlobalDictionaryWord.query().fetch()
        chunk_size = len(words) // 100
        for i, word in enumerate(words):
            data_object.append({"word": word.word,
                                "diff": i // chunk_size,
                                "used": word.used_times,
                                "tags": word.tags,
                                "deleted": word.deleted})
        output_file = gcs.open(get_gcs_filename(key), "w", "application/json")
        json.dump(data_object, output_file)
        output_file.close()
        config = GlobalConfiguration.load()
        old_key = config.dictionary_gcs_key
        config.dictionary_gcs_key = key
        config.put()
        if old_key:
            gcs.delete(get_gcs_filename(old_key))

class DictionaryHandler(APIRequestHandler):
    def get(self):
        import shutil
        config = GlobalConfiguration.load()
        key = config.dictionary_gcs_key
        if key in self.request.if_none_match:
            self.response.status = 304
            return
        dictionary_file = gcs.open(get_gcs_filename(key))
        shutil.copyfileobj(dictionary_file, self.response)
        dictionary_file.close()
        self.response.etag = key
