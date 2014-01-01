import json

from google.appengine.ext import ndb
import webapp2

'''
Example of json that should be gotten in order for server to change a user's dictionary
{"word_1": {"version": 1, "active": 1}, "word_2": {"version": 76, "active": 0}}
'''


class UserWord:
    def __init__(self, version=1, active=1):
        self.version = ndb.IntegerProperty(indexed=False)
        self.active = ndb.IntegerProperty(indexed=False)
        self.version = version
        self.active = active


class UserDictionary:
    def __init__(self, device_id):
        self.device_id = device_id
        self.list = dict()

    def update(self, word, version=1, active=1):
        self.list[word] = UserWord(version=version, active=active)

    def __str__(self):
        s = self.device_id + '<html> <br>'
        for i in self.list:
            s += i + ': ' + str(self.list[i].version) + ' ' + str(self.list[i].active) + '<br>'
        return s + '</html>'


class Change(webapp2.RequestHandler):
    def post(self, device_id):
        json_changes = self.request.get("diff")
        a = json.loads(json_changes)
        udict = UserDictionary(device_id)
        for i in a:
            udict.update(i, a[i]['version'], a[i]['active'])
        self.response.write(udict)


class Update(webapp2.RequestHandler):
    def get(self, device_id, device_version):
        self.response.write('Getting changes!' + str(device_id))
