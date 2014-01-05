import json

from google.appengine.ext import ndb
import webapp2

from objects.user_devices import get_user_by_device
from all_handler import AllHandler


class UserWord(ndb.Model):
    word = ndb.StringProperty()
    user = ndb.StringProperty()
    active = ndb.StringProperty(indexed=False)
    version = ndb.IntegerProperty(indexed=False)
    index = ndb.IntegerProperty(indexed=False)


def get_dictionary_version(user):  # Will return resulting version of the whole user's dictionary.
    wordlist = list(UserWord.query(UserWord.user == user))
    answer = 0
    for i in wordlist:
        if i.version > answer:
            answer = i.version
    return answer


class Change(AllHandler):
    def post(self, **kwargs):
        super(Change, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        json_changes = self.request.get("json")
        changes = json.loads(json_changes)
        dictionary_version = get_dictionary_version(user)
        for i in changes["words"]:
            wordlist = list(UserWord.query(UserWord.user == user and UserWord.word == i["word"]))
            for j in wordlist:
                j.key.delete()
            current_word = UserWord()
            current_word.active = i["status"]
            current_word.user = user
            current_word.word = i["word"]
            current_word.version = dictionary_version + 1
            current_word.index = int(i["index"])
            current_word.put()
        self.response.write(dictionary_version + 1)


def wordlist_to_json(wordlist, vers):
    json_strings = []
    for i in wordlist:
        cur = '{"word": "' + i.word + '", "version": "' + str(i.version) + '", "status": "' + i.active + \
              '", "index": "' + str(i.index) + '"}'
        json_strings.append(cur)
    json_string = "{\"version\": " + str(vers) + ", \"words\": ["
    for i in json_strings:
        json_string += i
        if i != json_strings[-1]:
            json_string += ', '
    return json_string + "]}"


class Update(AllHandler):
    def get(self, **kwargs):
        super(Update, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        version_on_device = kwargs.get("version")
        wordlist = list(UserWord.query(UserWord.user == user))
        rwordlist = []
        vers = get_dictionary_version(user)
        for i in wordlist:
            if i.version > int(version_on_device):
                rwordlist.append(i)
        self.response.write(wordlist_to_json(rwordlist, vers))


class Get(AllHandler):
    def get(self, **kwargs):
        super(Get, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        vers = get_dictionary_version(user)
        wordlist = list(UserWord.query(UserWord.user == user))
        self.response.write(wordlist_to_json(wordlist, vers))


class DrawWebpage(webapp2.RedirectHandler):
    def get(self):
        self.response.write("It works!")


class ProcWebpage(webapp2.RequestHandler):
    def post(self):
        self.response.write("It works!")
