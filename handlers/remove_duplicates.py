__author__ = 'nikolay'
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from handlers.legacy_game_history_handler import GameHistory
import hashlib


class RemoveDuplicates(ServiceRequestHandler):
    game_id = None

    def handle_game(self, game):
        if game.hash is not None:
            return
        hasher = hashlib.md5()
        hasher.update(game.json_string)
        game.hash = hasher.hexdigest()
        game.put_async()

    @ndb.toplevel
    def post(self):
        stage = self.request.get('stage')
        if stage == 'hash':
            GameHistory.query().map(self.handle_game)
        elif stage == 'mark':
            c = ndb.Cursor(urlsafe=self.request.get('cursor'))
            game, curs, more = GameHistory.query().fetch_page(1, start_cursor=c)
            game = game[0]
            if game is None:
                self.abort(200)
            if not game.ignored or game.hash is None:
                duplicates = GameHistory.query(GameHistory.hash == game.hash).fetch()
                duplicates.sort(key=lambda el: el.key.id())
                duplicates.pop()
                for el in duplicates:
                    el.ignored = True
                ndb.put_multi(duplicates)
            if more:
                taskqueue.add(url='/remove_duplicates',
                              params={'stage': 'mark', 'cursor': curs.urlsafe()},
                              queue_name='fast')
        elif stage == 'remove':
            ndb.delete_multi(GameHistory.query(GameHistory.ignored == True).fetch(keys_only=True))

