from handlers import WebRequestHandler
from webapp2_extras import i18n
import os

__author__ = 'Jakub'


class UserSettingsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UserSettingsHandler, self).__init__(*args, **kwargs)
        self.login_required = True

    def get(self, *args, **kwargs):
        user_key = self.user_key.get()
        locales = [name for name in os.listdir('./locale') if os.path.isdir(os.path.join('./locale', name))]
        self.draw_page('user_settings', locales=locales, locale=user_key.localization)

    def post(self, *args, **kwargs):
        user_key = self.user_key.get()
        user_key.localization = self.request.POST['selectLanguage']
        user_key.put()
        locales = [name for name in os.listdir('./locale') if os.path.isdir(os.path.join('./locale', name))]
        self.draw_page('user_settings', locales=locales, locale=user_key.localization)