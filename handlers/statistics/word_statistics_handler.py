__author__ = 'ivan'


from environment import JINJA_ENVIRONMENT
from environment import TRUESKILL_ENVIRONMENT
from handlers.base_handlers.web_request_handler import WebRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.ext import ndb


class WordStatisticsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WordStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        word = self.request.route_kwargs.get('word', None)
        entity = ndb.Key(GlobalDictionaryWord, word).get()
        render_data = {}
        render_data["word"] = entity if entity else None
        template = JINJA_ENVIRONMENT.get_template('templates/statistics/word_statistic.html')
        self.response.write(template.render(render_data))

