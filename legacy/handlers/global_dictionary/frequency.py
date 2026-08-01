
__author__ = 'ivan'

import json

from handlers import AdminRequestHandler, ServiceRequestHandler
from google.appengine.api import taskqueue
from google.appengine.ext import ndb


class WordFrequency(ndb.Model):
    word = ndb.StringProperty()
    frequency = ndb.FloatProperty()


class MakeDictionaryTaskQueueHandler(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(MakeDictionaryTaskQueueHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        words = json.loads(self.request.get("json"))
        for word in words:
            WordFrequency(word=word["w"], frequency=float(word["d"]), id=word["w"]).put()


class MakeDictionaryHandler(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(MakeDictionaryHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        in_json = json.loads(self.request.get("json"))
        to_add = []
        for word in in_json:
            to_add.append(word)
        taskqueue.add(url='/internal/frequency_dictionary/add/task_queue', params={"json": json.dumps(to_add)})


class DeleteDictionary(AdminRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteDictionary, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        taskqueue.add(url='/internal/frequency_dictionary/delete/task_queue')


class DeleteDictionaryTaskQueue(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DeleteDictionaryTaskQueue, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        for word in ndb.gql("SELECT word FROM WordFrequency").fetch():
            word.key.delete()