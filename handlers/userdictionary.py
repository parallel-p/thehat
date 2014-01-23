import json

from environment import JINJA_ENVIRONMENT

from objects.user_devices import get_user_by_device
from objects.user_dictionary_word import UserDictionaryWord
from base_handlers.api_request_handlers import APIRequestHandler
from base_handlers.web_request_handler import WebRequestHandler


class UserDictionaryHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(UserDictionaryHandler, self).__init__(*args, **kwargs)

    def _get_max_version(self, user):
        word = UserDictionaryWord.query(UserDictionaryWord.user == user). \
            order(-UserDictionaryWord.version).get()
        return word.version if word else 0

    def post(self, **kwargs):
        super(UserDictionaryHandler, self).get_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        changes = json.loads(self.request.get("json"))
        version = self._get_max_version(user) + 1
        for el in changes:
            current_word = (UserDictionaryWord.query(UserDictionaryWord.word ==
                                                     el["word"]).get() or
                            UserDictionaryWord())
            current_word.user = user
            current_word.status = el["status"]
            current_word.word = el["word"]
            current_word.version = version
            current_word.put()
        self.response.write(version)

    def get(self, **kwargs):
        super(UserDictionaryHandler, self).get_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        version_on_device = int(kwargs.get("version", 0))
        version = self._get_max_version(user)
        diff = UserDictionaryWord.query(UserDictionaryWord.version >
                                        version_on_device)
        self.response.write(json.dumps({"version": version,
                                        "words": [el.to_dict()
                                                  for el in diff]}))


class DrawWebpage(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DrawWebpage, self).__init__(*args, **kwargs)

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/editpersonaldictionary.html')
        try:
            wordlist = list(UserDictionary.query(UserDictionary.user == str(user.user_id())))[0].to_userword_array()
        except:
            wordlist = []
        rwordlist = []
        for i in wordlist:
            if i.active == "ok":
                rwordlist.append(i)
        render_data = {"words": rwordlist, "USER": user.user_id()}
        self.response.write(template.render(render_data))


class ProcWebpage(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ProcWebpage, self).__init__(*args, **kwargs)

    def post(self):
        words = self.request.get("words")
        user = self.request.get("user")
        words = [word.rstrip() for word in words.split('\n')]
        used = []
        version = get_dictionary_version(user)
        try:
            dict = list(UserDictionary.query(UserDictionary.user == user))[0]
            dict.key.delete()
            curwords = dict.to_userword_array()
        except:
            curwords = []
        index = 0
        for i in range(len(curwords)):
            if curwords[i].word in words:
                curwords[i].active = "ok"
                curwords[i].version = version + 1
                curwords[i].index = index
                index += 1
                used.append(curwords[i].word)
            else:
                curwords[i].active = "deleted"
                curwords[i].version = version + 1
                used.append(curwords[i].word)
        for i in words:
            if not (i in used) and (i != ""):
                curwords.append(UserDictionaryWord(word=i, user=user, active="ok", version=version + 1, index=index))
                index += 1
                used.append(i)
        a = UserDictionary(user=user)
        a.from_userword_array(curwords)
        a.put()
        template = JINJA_ENVIRONMENT.get_template('templates/personaldictionaryedit_ok.html');
        self.response.write(template.render())
