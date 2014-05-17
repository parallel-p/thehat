from handlers import WebRequestHandler

__author__ = 'ivan'

from objects.global_dictionary_word import GlobalDictionaryWord
from google.appengine.api import memcache
from random import randint

class WordStatisticsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WordStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        word = self.request.get('word', None)
        entity, games, top, bottom, rand, danger_top = None, None, None, None, None, None
        if word:
            entity = GlobalDictionaryWord.get(word)
        if not entity:
            danger_top = memcache.get("danger_top")
            if not danger_top:
                danger_top = GlobalDictionaryWord.query().order(-GlobalDictionaryWord.danger).fetch(limit=10)
                memcache.set("danger_top", danger_top, time=60*60*12)


            top = memcache.get("words_top")
            if not top:
                top = GlobalDictionaryWord.query().order(-GlobalDictionaryWord.E).fetch(limit=10)
                memcache.set("words_top", top, time=60*60*12)
            bottom = memcache.get("words_bottom")
            if not bottom:
                bottom = GlobalDictionaryWord.query().order(GlobalDictionaryWord.E).fetch(limit=10)
                memcache.set("words_bottom", bottom, time=60*60*12)
            q = GlobalDictionaryWord.query().filter(GlobalDictionaryWord.used_times > 0)
            c = memcache.get("used_words_count")
            if not c:
                c = q.count()
                memcache.set("used_words_count", c, time=60*60*12)
            if c >= 10:
                rand = q.fetch(limit=10, offset=randint(0, c-10))

        self.draw_page('statistics/word_statistic', word=word, word_entity=entity,
                       top=top if top else [], bottom=bottom if bottom else [], rand=rand if rand else [],
                       danger=danger_top if danger_top else [])

