from google.appengine.ext import ndb

import webapp2
import json
import logging
import objects.user_devices



'''
Example of json that should be gotten in order for server to change a user's dictionary
[{"word: "word_1", "version": 0, "active": 1}, {"word": "word2", "version": 1, "active": 0}]
'''

class UserWord(ndb.Model):
    word = ndb.StringProperty()
    user = ndb.StringProperty()
    active = ndb.IntegerProperty(indexed=False)
    version = ndb.IntegerProperty(indexed=False)
    def get_version(self):
        return self.version

def get_dictionary_version(user): # Will return resulting version of dictionary of user user
    user = objects.user_devices.get_user_by_device(user)
    wordlist = list(UserWord.query(UserWord.user == user))
    answer = 0
    for i in wordlist:
        if i.get_version() > answer:
            answer = i.get_version()
    return answer

class Change(webapp2.RequestHandler):
    def post(self, user):
        user = objects.user_devices.get_user_by_device(user)
        json_changes = self.request.get("json")
        changes = json.loads(json_changes)
        curmax_version = -1
        for i in changes:
            current_word = UserWord()
            current_word.active = i["active"]
            current_word.user = user
            current_word.word = i["word"]
            current_word.version = i["version"]
            wordlist = list(UserWord.query(UserWord.user == user))
            for i in wordlist:
                i.key.delete()
            current_word.put()
            if current_word.version > curmax_version:
                curmax_version = current_word.version
        self.response.write(max(get_dictionary_version(user), curmax_version))

class Update(webapp2.RequestHandler):
    def get(self, user, version_on_device):
        user = objects.user_devices.get_user_by_device(user)
        if get_dictionary_version(user) > int(version_on_device):
            wordlist = list(UserWord.query(UserWord.user == user))
            json_strings = []
            for i in wordlist:
                if i.get_version() > int(version_on_device):
                    cur = dict()
                    cur["word"] = i.word
                    cur["version"] = str(i.version)
                    cur["active"] = str(int(i.active))
                    json_strings.append(cur)
            self.response.write(str(json_strings))
