from google.appengine.ext import ndb

import webapp2
import json
import objects.user_devices

class UserWord(ndb.Model):
    word = ndb.StringProperty()
    user = ndb.StringProperty()
    active = ndb.IntegerProperty(indexed=False)
    version = ndb.IntegerProperty(indexed=False)
    index = ndb.IntegerProperty(indexed=False)

def get_dictionary_version(user): # Will return resulting version of the whole user's dictionary.
    wordlist = list(UserWord.query(UserWord.user == user))
    answer = 0
    for i in wordlist:
        if i.version > answer:
            answer = i.version
    return answer

class Change(webapp2.RequestHandler):
    def post(self, user):
        user = objects.user_devices.get_user_by_device(user)
        json_changes = self.request.get("json")
        changes = json.loads(json_changes)
        dictionary_version = get_dictionary_version(user)
        for i in changes:
            wordlist = list(UserWord.query(UserWord.user == user and UserWord.word == i["word"]))
            for j in wordlist:
                j.key.delete()
            current_word = UserWord()
            current_word.active = int(i["active"])
            current_word.user = user
            current_word.word = i["word"]
            current_word.version = dictionary_version + 1
            current_word.index = int(i["index"])
            current_word.put()
        self.response.write(dictionary_version + 1)

def wordlist_to_json(wordlist):
    json_strings = []
    for i in wordlist:
        cur = '{"word": "' + i.word + '", "version": "' + str(i.version) + '", "active": "' + str(i.active) +\
              '", "index": "' + str(i.index) + '"}'
        json_strings.append(cur)
    json_string = "["
    for i in json_strings:
        json_string += i
        if i != json_strings[-1]:
            json_string += ', '
    return json_string + "]"



class Update(webapp2.RequestHandler):
    def get(self, user, version_on_device):
        user = objects.user_devices.get_user_by_device(user)
        wordlist = list(UserWord.query(UserWord.user == user))
        rwordlist = []
        for i in wordlist:
            print(i.word, i.version, version_on_device)
            if i.version > int(version_on_device):
                print('thst', i.word, i.version)
                rwordlist.append(i)
        self.response.write(wordlist_to_json(rwordlist))


class Get(webapp2.RequestHandler):
    def get(self, user):
        user = objects.user_devices.get_user_by_device(user)
        wordlist = list(UserWord.query(UserWord.user == user))
        self.response.write(wordlist_to_json(wordlist))
