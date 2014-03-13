__author__ = 'ivan'

import webapp2
import os


def setCurrentUser(email, user_id, is_admin=False):
    os.environ['USER_EMAIL'] = email or ''
    os.environ['USER_ID'] = user_id or ''
    os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'


def logoutCurrentUser():
    setCurrentUser(None, None)


def make_request(url, type, admin=False, body=None):
    request = webapp2.Request.blank(url)
    request.method = type
    if body:
        request.body = body
    setCurrentUser('usermail@gmail.com', '1', admin)
    return request