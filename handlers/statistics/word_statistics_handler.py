__author__ = 'ivan'


from environment import JINJA_ENVIRONMENT
from handlers.base_handlers.web_request_handler import WebRequestHandler


class WordStatisticsHandler(WebRequestHandler):

    def __init__(self, *args, **kwargs):
        super(WordStatisticsHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        template = JINJA_ENVIRONMENT.get_template('templates/statistics/word_statistic.html')
        self.response.write(template.render({}))
