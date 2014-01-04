__author__ = 'ivan'

import json

from all_handler import AllHandler
from objects.complained_word import ComplainedWord
from environment import JINJA_ENVIRONMENT


class ComplainWordHandler(AllHandler):
    def post(self, **kwargs):
        super(ComplainWordHandler, self).set_device_id(**kwargs)
        complained_word_json_list = \
            json.loads(self.request.get(r'json'))
        for current_word_json in complained_word_json_list:
            current_word = ComplainedWord(device_id=self.device_id,
                                          word=current_word_json['word'],
                                          reason=current_word_json['reason'])
            if 'replace_word' in current_word_json:
                current_word.replacement_word = \
                    current_word_json['replace_word']
            current_word.put()

    def get(self, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/complained_words.html')
        cnt = 0
        render_data = {"words": []}
        for word in ComplainedWord.all():
            word_render = word
            word_render.cnt = cnt
            if word.replacement_word is None:
                word_render.replacement_word = ''
            render_data["words"].append(word_render)
            cnt += 1
        self.response.write(template.render(render_data))

