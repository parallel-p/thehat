# Author: vad@drobinin.com
# News Feed Handlers,
# v 0.2


from google.appengine.ext import db
from webapp2_extras import json
import webapp2
import os
import time

from environment import *


class News(db.Model):
    title = db.StringProperty()
    id = db.IntegerProperty()
    text = db.TextProperty()
    location = db.StringProperty()
    timestamp = db.IntegerProperty()
    url = db.StringProperty()

    def make_json(self):
        return {'title': self.title,
                'text': self.text,
                'location': self.location,
                'id': self.id,
                'url': self.url,
                'timestamp': self.timestamp}


NEWS_DB = db.GqlQuery("SELECT * FROM News ORDER BY id")
NEWS_AMOUNT = 10
ADMIN_PASSWORD = '123456'  # Because there is no OpenID auth


def doRender(handler, tname='index.html', values={}):
    temp = os.path.join(
        os.path.dirname(__file__),
        'templates/' + tname)
    if not os.path.isfile(temp):
        return False

    # Make a copy and add the path
    new_val = dict(values)
    new_val['path'] = handler.request.path
    new_val['db'] = NEWS_DB
    template = ENVIRONMENT.get_template('templates/' + tname)
    out_str = template.render(new_val)
    handler.response.out.write(out_str)
    return True


def get_last_id():
    news = list(db.GqlQuery("SELECT * FROM News ORDER BY id"))
    return len(news)


def json_with_news(id):
    json_obj = {'news_items': [], "recent_id": 0}
    dtb = db.GqlQuery("SELECT * FROM News WHERE id > :1 ORDER BY id", int(id))
    for news in dtb.run(limit=NEWS_AMOUNT):
        json_obj['news_items'].append(news.make_json())
    json_obj['recent_id'] = get_last_id()
    return json.encode(json_obj)


class LoginPageHandler(webapp2.RequestHandler):
    def get(self):
        doRender(self, 'loginscreen.html')

    def post(self):
        acct = self.request.get('account')
        pw = self.request.get('password')

        if pw == '' or acct == '':
            doRender(
                self,
                'loginscreen.html',
                {'error': 'Specify Login and password'}
            )
        elif pw == ADMIN_PASSWORD:
            doRender(self, 'loggedin.html', {})
        else:
            doRender(
                self,
                'loginscreen.html',
                {'error': 'Incorrect password'}
            )


class LoadNewsHandler(webapp2.RequestHandler):
    def get(self, last_id):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json_with_news(last_id))


class ListOfNewsHandler(webapp2.RequestHandler):
    def get(self):
        doRender(self, 'loggedin.html')


class AddNewsHandler(webapp2.RequestHandler):
    def get(self):
        doRender(self, 'addnewsscreen.html')

    def post(self):
        # TODO: Add normal cookies
        title = self.request.get('title')
        id = get_last_id() + 1
        text = self.request.get('text')
        location = self.request.get('location')
        url = self.request.get('url')
        news = News(
            title=title,
            id=id,
            text=text,
            location=location,
            url=url,
            timestamp=int(time.time())*1000)  # Unix-time in milliseconds
        news.put()
        self.redirect('/listofnews')


class ShowNewsHandler(webapp2.RequestHandler):
    def get(self, id):
        news = db.GqlQuery('SELECT * FROM News WHERE id = :1', int(id))
        post = news.run().next()
        doRender(self, 'post.html', {'id': id, 'post': post})
