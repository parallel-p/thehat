__author__ = 'ivan'

from google.appengine.ext import db
from google.appengine.api import users

from objects.complained_word import ComplainedWord
from environment import JINJA_ENVIRONMENT
import constants
from objects.global_dictionary_word import GlobalDictionaryWord
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from objects.GlobalDictionaryJSON import GlobalDictionaryJson
import json
import time


class GlobalDictionaryWordList(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AdminRequestHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/global_word_editor.html')
        curr_json = GlobalDictionaryJson.get_by_key_name('json')
        render_data = {'words':[]}
        num = 0
        word_cnt = 0
        id = int(kwargs.get('id'))
        if curr_json is not None:
            for i in json.loads(curr_json.json):
                word_cnt += 1
                if i['tags'].find('-deleted') != -1 or word_cnt <= id * 200 or word_cnt > (id + 1) * 200:
                    continue
                word = GlobalDictionaryWord(cnt=num, word=i['word'], E=i['E'], D=i['D'], tags=i['tags'])
                num += 1
                render_data['words'].append(word)
        render_data['quantity'] = num
        render_data['all_num'] = word_cnt
        self.response.write(template.render(render_data))


class GlobalDictionaryDeleteWord(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GlobalDictionaryDeleteWord, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        word_to_delete = self.request.get("word")
        entity = GlobalDictionaryWord.get_by_id(word_to_delete)
        if entity is not None and entity.tags.find("-deleted") == -1:
            entity.tags += "-deleted"
        entity.put()
        #TODO: i think we must date Json one or two times a day.
        time.sleep(1)
        GlobalDictionaryJson.update_json()



