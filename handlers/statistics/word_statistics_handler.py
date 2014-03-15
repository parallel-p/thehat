__author__ = 'ivan'

import logging
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
        word = self.request.get('word', None)
        entity = None
        if word:
            entity = ndb.Key(GlobalDictionaryWord, word).get()
        self.draw_page('statistics/word_statistic', word=word, word_entity=(entity if entity else None))

