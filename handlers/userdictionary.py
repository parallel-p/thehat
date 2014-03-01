import json

from environment import JINJA_ENVIRONMENT

from objects.user_dictionary_word import UserDictionaryWord
from base_handlers.api_request_handlers import AuthorizedAPIRequestHandler
from base_handlers.web_request_handler import WebRequestHandler
from google.appengine.api import users


class UserDictionaryHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(UserDictionaryHandler, self).__init__(*args, **kwargs)

    def post(self, **kwargs):
        changes = json.loads(self.request.get("json"))
        version = _get_max_version(self.user_key) + 1
        for el in changes:
            current_word = (UserDictionaryWord.query(self.user_key, UserDictionaryWord.word ==
                                                     el["word"]).get() or
                            UserDictionaryWord(owner=self.device_key))
            current_word.populate(version=version, **el)
            current_word.put()
        self.response.write(version)

    def get(self, version=0, **kwargs):
        version_on_device = int(version)
        version = _get_max_version(self.user_key)
        diff = UserDictionaryWord.query(self.user_key, UserDictionaryWord.version >
                                        version_on_device)
        self.response.write(json.dumps({"version": version,
                                        "words": [el.to_dict(exclude=('owner',))
                                                  for el in diff]}))


def _get_max_version(user):
    word = UserDictionaryWord.query(user).order(-UserDictionaryWord.version).get()
    return word.version if word else 0


class DrawWebpage(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(DrawWebpage, self).__init__(*args, **kwargs)

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/editpersonaldictionary.html')
        wordlist = [el.word for el in UserDictionaryWord.query(self.user_key).fetch()]
        rwordlist = filter(lambda x: (x.active == "ok"), wordlist)
        render_data = {"words": rwordlist, "USER": self.user.user_id()}
        self.response.write(template.render(render_data))


class ProcWebpage(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ProcWebpage, self).__init__(*args, **kwargs)

    def post(self):
        words = self.request.get("words")
        user = self.request.get("user")
        words = [word.rstrip() for word in words.split('\n')]
        used = []
        version = _get_max_version(self.user_key)
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
        template = JINJA_ENVIRONMENT.get_template('templates/personaldictionaryedit_ok.html')
        self.response.write(template.render())
