from handlers.base_handlers.admin_request_handler import AdminRequestHandler

__author__ = 'ivan'

from objects.unknown_word import UnknownWord


class GetWordPageHandler(AdminRequestHandler):

    def __init(self, *args, **kwargs):
        super(GetWordPageHandler, self).__init__(*args, **kwargs)

    def get(self):
        words = UnknownWord.query().order(-UnknownWord.times_used).filter(UnknownWord.ignored == False).fetch()
        self.draw_page('unknown_word_page', word_list = words)