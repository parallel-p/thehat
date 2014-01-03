__author__ = 'ivan'

import json

from all_handler import AllHandler
from objects.complained_word import ComplainedWord


class ComplainWordHandler(AllHandler):
    def post(self, **kwargs):
        super(ComplainWordHandler, self).set_device_id(**kwargs)
        complained_word_json_list = \
            json.loads(self.request.get(r'complained_words'))

        for current_word_json in complained_word_json_list:
            current_word = ComplainedWord(device_id=self.device_id,
                                          word=current_word_json['word'],
                                          cause=current_word_json['cause'])
            if 'replace_word' in current_word_json:
                current_word.replacement_word = \
                    current_word_json['replace_word']
            current_word.put()


    def get(self, **kwargs):
        res = '<table border="1">'
        res += '''<tr><td>#</td><td>device_id</td><td>word</td>
                  <td>cause</td><td>replace_to</td></tr>'''
        cnt = 0
        for word in ComplainedWord.all():
            res += '''
                    <tr>
                        <td>{0}</td>
                        <td>{1}</td>
                        <td>{2}</td>
                        <td>{3}</td>
                        <td>{4}</td>
                    </tr>
                    '''.format(cnt, word.device_id, word.word, word.cause,
                               word.replacement_word if word.replacement_word else '')
            cnt += 1
        res += "</table"
        self.response.write(res)

