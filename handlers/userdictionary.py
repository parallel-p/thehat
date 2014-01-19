import json

from google.appengine.ext import ndb
import webapp2

from environment import JINJA_ENVIRONMENT

from objects.user_devices import get_user_by_device
from all_handler import AllHandler
from google.appengine.api import users

class UserDictionary(ndb.Model):
    user = ndb.StringProperty()
    id = ndb.IntegerProperty()
    version = ndb.IntegerProperty(indexed=False, default=0)


class UserWord(ndb.Model):
    word = ndb.StringProperty()
    status = ndb.StringProperty(indexed=False, default="")
    version = ndb.IntegerProperty(default=0)


class List(AllHandler):
    def get(self, **kwargs):
        super(List, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        dicts = UserDictionary.query(UserDictionary.user == user)
        self.response.write(json.dumps([el.to_dict() for el in dicts]))


class Change(AllHandler):
    def post(self, **kwargs):
        super(Change, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        dict_id = int(kwargs.get("id"))
        changes = json.loads(self.request.get("json"))
        dictionary = (UserDictionary.query(UserDictionary.user == user, UserDictionary.id == dict_id).get() or UserDictionary(user=user,id=dict_id)).put().get()
        dictionary.version += 1
        for el in changes["words"]:
            current_word = UserWord.query(UserWord.word == el["word"], ancestor=dictionary.key).get() or UserWord(parent=dictionary.key)
            current_word.status = el["status"]
            current_word.word = el["word"]
            current_word.version = dictionary.version
            current_word.put()
        dictionary.put()
        self.response.write(dictionary.version)


class GetDiff(AllHandler):
    def get(self, **kwargs):
        super(GetDiff, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        dict_id = int(kwargs.get("id"))
        version_on_device = int(kwargs.get("version", 0))
        dictionary = UserDictionary.query(UserDictionary.user == user, UserDictionary.id == dict_id).get()
        if dictionary is None:
            self.error(404)
            return
        if dictionary.version <= version_on_device:
            diff = []
        else:
            diff = UserWord.query(UserWord.version > version_on_device, ancestor=dictionary.key)
        self.response.write(json.dumps({"version": dictionary.version, "words": [el.to_dict() for el in diff]}))


class DrawWebpage(webapp2.RedirectHandler):
    def get(self):
        user = users.get_current_user()
        if user is None:
            self.redirect(users.create_login_url('/generate_pin'))
        else:
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



class ProcWebpage(webapp2.RequestHandler):
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
                curwords.append(UserWord(word=i, user=user, active="ok", version=version + 1, index=index))
                index += 1
                used.append(i)
        a = UserDictionary(user=user)
        a.from_userword_array(curwords)
        a.put()
        template = JINJA_ENVIRONMENT.get_template('templates/personaldictionaryedit_ok.html');
        self.response.write(template.render())
