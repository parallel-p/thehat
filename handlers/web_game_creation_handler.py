__author__ = 'ivan'


from environment import JINJA_ENVIRONMENT
from handlers.base_handlers.web_request_handler import WebRequestHandler


class WebGameCreationHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WebGameCreationHandler, self).__init__(*args, **kwargs)
        self.login_required = True

    def get(self, *args, **kwargs):
        self.draw_page('create_game')
