__author__ = 'ivan'

import logging
from environment import JINJA_ENVIRONMENT
from environment import TRUESKILL_ENVIRONMENT
from handlers.base_handlers.web_request_handler import WebRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.ext import ndb
from google.appengine.api import memcache
from random import randint

class WordStatisticsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WordStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        word = self.request.get('word', None)
        entity, games, top, bottom, rand = None, None, None, None, None
        if word:
            entity = ndb.Key(GlobalDictionaryWord, word).get()
            games = []
            for id in entity.used_games:
                games.append(ndb.Key('GameLog', id).urlsafe())
            for id in entity.used_legacy_games:
                games.append(ndb.Key('GameHistory', id).urlsafe())

        if not entity:
            top = memcache.get("words_top")
            if not top:
                top = GlobalDictionaryWord.query(projection=[GlobalDictionaryWord.E, GlobalDictionaryWord.word]).\
                    order(-GlobalDictionaryWord.E).fetch(limit=10)
                memcache.set("words_top", top)
            bottom = memcache.get("words_bottom")
            if not bottom:
                bottom = GlobalDictionaryWord.query(projection=[GlobalDictionaryWord.E, GlobalDictionaryWord.word]).\
                    order(GlobalDictionaryWord.E).fetch(limit=10)
                memcache.set("words_bottom", bottom)
            q = GlobalDictionaryWord.query(projection=[GlobalDictionaryWord.E, GlobalDictionaryWord.word]).\
                filter(GlobalDictionaryWord.used_times > 0)
            c = memcache.get("used_words_count")
            if not c:
                c = q.count()
                memcache.set("used_words_count", c)
            rand = q.fetch(limit=10, offset=randint(0, c-10))
        self.draw_page('statistics/word_statistic', word=word, word_entity=entity, games=games,
                       top=top, bottom=bottom, rand=rand)

