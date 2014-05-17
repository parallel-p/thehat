#TODO: this file is obsolete and must be rewritten
from handlers import AdminRequestHandler

__author__ = 'ivan'

import json

from environment import JINJA_ENVIRONMENT
from objects.global_dictionary_word import GlobalDictionaryWord
from objects.GlobalDictionaryJSON import GlobalDictionaryJson


class GlobalDictionaryWordList(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(GlobalDictionaryWordList, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        #TODO : add normal editor
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



