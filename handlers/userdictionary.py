import json

from objects.user_dictionary_word import UserDictionaryWord
from base_handlers.api_request_handlers import AuthorizedAPIRequestHandler
from base_handlers.web_request_handler import WebRequestHandler


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
        word_list = filter(lambda x: (x.status == "ok"), UserDictionaryWord.query(self.user_key).fetch())
        self.draw_page('editpersonaldictionary', word=word_list)


class ProcWebpage(WebRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ProcWebpage, self).__init__(*args, **kwargs)

    def post(self):
        added = self.request.get_all("added[]")
        removed = self.request.get_all("removed[]")
        version = _get_max_version(self.user_key) + 1
        for word in removed:
            w = UserDictionaryWord.query(self.user_key, UserDictionaryWord.word == word).get()
            w.status = "removed"
            w.version = version
            w.put()
        for word in added:
            UserDictionaryWord(word=word, status="ok", version=version, owner=self.user_key).put()


def merge_user_dictionary_data(user_key, device_key):
    device_words = UserDictionaryWord.query(device_key).fetch()
    version = max(_get_max_version(user_key), _get_max_version(device_key)) + 1
    for word in device_words:
        user_word = UserDictionaryWord.query(user_key, UserDictionaryWord.word == word.word).get()
        if user_word:
            user_word.status = "ok" if word.status == "ok" or user_word.status == "ok" else "removed"
            user_word.created = min(user_word.created, word.created)
            user_word.used = max(user_word.used, word.used)
            user_word.version = version
            user_word.put()
            del word.key
        else:
            word.owner = user_key
            word.put()
    user_words = UserDictionaryWord.query(user_key).fetch()
    for word in user_words:
        word.version = version
        word.put()
