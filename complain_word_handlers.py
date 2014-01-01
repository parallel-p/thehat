__author__ = 'ivan'

import json

from all_handler import AllHandler
from objects.complained_word import ComplainedWord


class ComplainWordHandler(AllHandler):
    def post(self, **kwargs):
        super(ComplainWordHandler, self).set_device_id(**kwargs)
        complained_word_json_list = \
            json.loads(self.request.get(r'complained_words'))
        for current_complained_word_json in complained_word_json_list:
            current_complained_word = ComplainedWord()
            current_complained_word.word = current_complained_word_json['word']
            current_complained_word.cause = \
                int(current_complained_word_json['cause'])
            current_complained_word.device_id = self.device_id
            if 'replace_word' in current_complained_word_json:
                current_complained_word.replacement_word = \
                    current_complained_word_json['replace_word']
            current_complained_word.put()
        self.response.write('post, ok, device_id ='
                            '{0}\n'.format(self.device_id))

    def get(self, **kwargs):
        res = "<table>"
        cnt = 0
        for word in ComplainedWord.all():
            res += '''<tr>
                <td>{0}</td>
                <td>{1}</td>
                <td>{2}</td>
                <td>{3}</td>
                <td>{4}</td>
            </tr>'''.format(cnt, word.device_id, word.word, word.cause, word.replacement_word)
            cnt += 1
        res += "</table"
        self.response.write(res)

