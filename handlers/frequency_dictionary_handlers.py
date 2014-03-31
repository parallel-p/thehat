__author__ = 'ivan'

from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
import json


class WordFrequency(ndb.Model):

    word = ndb.StringProperty()
    frequency = ndb.IntegerProperty()


class MakeDictionaryTaskQueueHandler(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(MakeDictionaryTaskQueueHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        words = json.loads(self.request.get("json"))
        for word in words:
            WordFrequency(word=word["w"], frequency=int(word["d"]), id=word["w"]).put()


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