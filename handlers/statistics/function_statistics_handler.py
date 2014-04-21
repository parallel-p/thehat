__author__ = 'ivan'

from objects.global_dictionary_word import GlobalDictionaryWord
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from handlers.base_handlers.admin_request_handler import AdminRequestHandler

from google.appengine.api import taskqueue
from google.appengine.ext import ndb
import heapq
import json


class Function(ndb.Model):
    name = ndb.StringProperty(repeated=False)
    description = ndb.StringProperty(indexed=False)
    code = ndb.TextProperty(indexed=False, repeated=False)


class Result(ndb.Model):
    function_name = ndb.StringProperty()
    json = ndb.TextProperty(indexed=False)


class push_results_task_queue(ServiceRequestHandler):

    def post(self):
        function_name = self.request.get("name")
        top50 = self.request.get("top")
        curr_result = ndb.Key(Result, function_name).get()
        if curr_result is not None:
            curr_result.function_name = function_name
            curr_result.json = top50
        else:
            curr_result = Result(function_name=function_name, json=top50, id=function_name)
        curr_result.put()


class UpdateFunctionsStatisticsHandler(ServiceRequestHandler):

    def post(self):
        taskqueue.add(url='/internal/statistics/functions/update/task_queue')


class UpdateFunctionsStatisticsHandlerTaskQueue(ServiceRequestHandler):

    def post(self):
        results = {}
        functions = {}
        names = []
        for function in Function.query().fetch():
            exec function.code in functions
            results[function.name] = {}
            names.append(function.name)
        for word in GlobalDictionaryWord.query().fetch():
            for function_name in names:
                res = functions[function_name](word)
                if res is not None:
                    results[function_name][word.word] = functions[function_name](word)
        for function_name in results:
            top50 = [(key, results[function_name][key]) for key in heapq.nlargest(50, results[function_name],
                                                                                key=results[function_name].get)]
            taskqueue.add(url='/internal/statistics/functions/update/task_queue/push_results',
                              params={'name': function_name, 'top': json.dumps(top50)})

            
class AddFunctionHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AddFunctionHandler, self).__init__(*args, **kwargs)

    def get(self):
        self.draw_page('/statistics/add_function_handler')

    def post(self):
        code = self.request.get("code")
        name = self.request.get("name")
        description = self.request.get("descr")
        curr = ndb.Key(Function, name).get()
        if curr is None:
            Function(name=name, code=code, description=description, id=name).put()


class ResultShowHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(ResultShowHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        function_name = self.request.get('function', None)
        all = [i.name for i in ndb.gql("SELECT name FROM Function").fetch()]
        result, function = None, None
        if function_name is not None:
            _result = ndb.Key(Result, function_name).get()
            function = ndb.Key(Function, function_name).get()
            if _result is not None:
                result = json.loads(_result.json)

        self.draw_page('statistics/show_results_screen', function=function, result=result, all=all)
