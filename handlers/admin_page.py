from handlers import AdminRequestHandler

__author__ = 'ivan'


class AdminPage(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(AdminPage, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        self.draw_page('admin')