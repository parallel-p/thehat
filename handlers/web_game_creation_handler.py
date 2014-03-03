__author__ = 'ivan'


from environment import JINJA_ENVIRONMENT
from handlers.base_handlers.web_request_handler import WebRequestHandler


class WebGameCreationHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WebGameCreationHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/create_game.html')
        self.response.write(template.render({}))
