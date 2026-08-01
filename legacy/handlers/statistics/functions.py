from handlers import AdminRequestHandler, ServiceRequestHandler

__author__ = 'ivan'

from objects.global_dictionary import GlobalDictionaryWord

from google.appengine.api import taskqueue
from google.appengine.ext import ndb
import heapq
import json


class Function(ndb.Model):
    name = ndb.StringProperty(repeated=False)
    description = ndb.StringProperty(indexed=False)
    code = ndb.TextProperty(indexed=False, repeated=False)


class FunctionResult(ndb.Model):
    top = ndb.PickleProperty()


def get_top(name):
    top = ndb.Key(FunctionResult, name).get()
    if not top:
        raise ValueError()
    top = json.loads(top.top).sort()
    return top


class UpdateFunctionsStatisticsHandler(ServiceRequestHandler):
    def post(self):
        taskqueue.add(url='/internal/statistics/functions/update/task_queue')


class Elem:
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
        for function in Function.query().fetch():
            exec function.code in functions
            results[function.name] = []
        for index, word in enumerate(GlobalDictionaryWord.query().fetch()):
            for name, result in results:
                res = functions[name](word)
                if res is not None:
                    if len(result) <= 50:
                        result.append(Elem(res, word.word))
                    else:
                        heapq.heappushpop(result, Elem(res, word.word))
        for name, result in results:
            FunctionResult(top=result, id=name).put()

            
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
        function_names = Function.query().fetch(keys_only=True)
        result, function = None, None
        if function_name is not None:
            function = ndb.Key(Function, function_name).get()
            result = get_top(function_name)

        self.draw_page('statistics/show_results_screen', function=function, result=result, all=function_names)
