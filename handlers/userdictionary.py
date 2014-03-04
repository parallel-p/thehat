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
        wordlist = filter(lambda x: (x.status == "ok"), UserDictionaryWord.query(self.user_key).fetch())
        render_data = {"words": wordlist, "USER": self.user.user_id()}
        self.response.write(template.render(render_data))


class ProcWebpage(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ProcWebpage, self).__init__(*args, **kwargs)

    def post(self):
        added = self.request.get("added[]", allow_multiple=True)
        removed = self.request.get("removed[]", allow_multiple=True)
        print(added, removed)
        version = _get_max_version(self.user_key) + 1
        for word in removed:
            w = UserDictionaryWord.query(self.user_key, UserDictionaryWord.word == word).get()
            w.status = "removed"
            w.version = version
            w.put()
        for word in added:
            UserDictionaryWord(word=word, status="ok", owner=self.user_key).put()


def merge_data(user, device):
    device_words = UserDictionaryWord.query(device).fetch()
    version = max(_get_max_version(user), _get_max_version(device)) + 1
    for word in device_words:
        user_word = UserDictionaryWord.query(user, UserDictionaryWord.word == word.word).get()
        if user_word:
            user_word.status = "ok" if word.status == "ok" or user_word.status == "ok" else "removed"
            user_word.created = min(user_word.created, word.created)
            user_word.used = max(user_word.used, word.used)
            user_word.put()
            del word.key
        else:
            word.owner = user
            word.put()
    user_words = UserDictionaryWord.query(user).fetch()
    for word in user_words:
        word.version = version
        word.put()
