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


class elem:

    def __init__(self, res, word):
        self.word = word
        self.res = res

    def __lt__(self, other):
        if self.res == other.res:
            return self.word < other.word
        else:
            return self.res < other.res


class UpdateFunctionsStatisticsHandlerTaskQueue(ServiceRequestHandler):

    def post(self):
        results = {}
        functions = {}
        names = []
        for function in Function.query().fetch():
            exec function.code in functions
            results[function.name] = []
            names.append(function.name)
        cnt = 0
        for index, word in enumerate(GlobalDictionaryWord.query().fetch()):
            cnt += 1
            for function_name in names:
                res = functions[function_name](word)
                if res is not None:
                    if cnt <= 50:
                        results[function_name].append(elem(res, word.word))
                    else:
                        heapq.heappushpop(results[function_name], elem(res, word.word))
        for function_name in results:
            top50 = {i.word: i.res for i in results[function_name]}
            taskqueue.add(url='/internal/statistics/functions/update/task_queue/push_results',
                              params={'name': function_name, 'top': json.dumps(top50)})

            
class AddFunctionHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AddFunctionHandler, self).__init__(*args, **kwargs)

    def get(self):
        self.draw_page('/statistics/add_function_handler')

    def post(self):
        code = self.request.get("code")
        first = code.find("def")
        last = code.find("(")
        name = code[first+3:last].strip()
        description = self.request.get("descr")
        curr = ndb.Key(Function, name).get()
        if curr is None:
            Function(name=name, code=code, description=description, id=name).put()


class CronUpdateResHandlers(ServiceRequestHandler):

    def init(self, *args, **kwargs):
        super(CronUpdateResHandlers, self).__init__(*args, **kwargs)

    def get(self):
        taskqueue.add(url='/internal/statistics/functions/update/task_queue')


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
                result = [(i, result[i]) for i in result]

        self.draw_page('statistics/show_results_screen', function=function, result=result, all=all)
