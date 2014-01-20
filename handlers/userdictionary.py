import json

from google.appengine.ext import ndb
import webapp2

from environment import JINJA_ENVIRONMENT

from objects.user_devices import get_user_by_device
from all_handler import AllHandler
from google.appengine.api import users

class UserWord(ndb.Model):
    user = ndb.StringProperty()
    word = ndb.StringProperty()
    status = ndb.StringProperty(indexed=False, default="")
    dictionary = ndb.IntegerProperty(indexed=False, default=0)
    version = ndb.IntegerProperty(default=0)


class UserDictionaryHandler(AllHandler):
    def _get_max_version(self, user):
        word = UserWord.query(UserWord.user == user).order(-UserWord.version).get()
        return word.version if word else 0

    def post(self, **kwargs):
        super( UserDictionaryHandler, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        changes = json.loads(self.request.get("json"))
        version = self._get_max_version(user) + 1
        for el in changes["words"]:
            current_word = UserWord.query(UserWord.word == el["word"]).get() or UserWord()
            current_word.user = user
            current_word.status = el["status"]
            current_word.word = el["word"]
            current_word.version += version
            current_word.put()
        self.response.write(version)

    def get(self, **kwargs):
        super(UserDictionaryHandler, self).set_device_id(**kwargs)
        user = get_user_by_device(self.device_id)
        version_on_device = int(kwargs.get("version", 0))
        version = self._get_max_version(user)
        diff = UserWord.query(UserWord.version > version_on_device)
        self.response.write(json.dumps({"version": version, "words": [el.to_dict() for el in diff]}))


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
