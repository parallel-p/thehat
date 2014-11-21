# -*- coding: utf-8 -*-
from handlers import AdminRequestHandler
from google.appengine.api import taskqueue
from random import randint

class OperationsAdminPage(AdminRequestHandler):
    urls = ['/internal/recalc_all_logs',
            '/remove_duplicates',
            '/remove_duplicates',
            '/remove_duplicates',
            "/cron/update_plots/start/admin",
            "/service/generate_dictionary"]
    params = [{}, {'stage': 'hash'}, {'stage': 'mark'}, {'stage': 'remove'}, {}, {}]
    task_name = [u"Пересчитать статистику",
            u"Посчитать хэши старых игр",
            u"Пометить дубликаты старых игр",
            u"Удалить дубликаты старых игр",
            u"Обновить все графики",
            u"Сгенерировать JSON словаря"]

    def post(self):
        code = self.request.get('code')
        action = int(self.request.get('action'))
        message = 0
        if code:
            if code == self.request.get('ans'):
                if action == 5:
                    self.redirect(self.urls[action-1])
                else:
                    taskqueue.add(url=self.urls[action-1], params=self.params[action-1])
                    message = 1
            else:
                message = 2
        a = randint(10, 99)
        b = randint(10, 99)
        self.draw_page('operations', message=message, a=a, b=b, names=self.task_name,
                last_value=int(action))

    def get(self):
        a = randint(10, 99)
        b = randint(10, 99)
        self.draw_page('operations', message=0, a=a, b=b, names=self.task_name)
