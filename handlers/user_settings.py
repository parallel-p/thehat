from handlers import WebRequestHandler
from webapp2_extras import i18n
import os

__author__ = 'Jakub'


class UserSettingsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UserSettingsHandler, self).__init__(*args, **kwargs)
        self.login_required = True

    def get(self, *args, **kwargs):
        locales = [name for name in os.listdir('./locale') if os.path.isdir(os.path.join('./locale', name))]
        self.draw_page('user_settings', locales=locales, locale=i18n.get_i18n().locale)

    def post(self, *args, **kwargs):
        print "test"