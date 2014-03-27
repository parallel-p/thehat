__author__ = 'nikolay'
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from handlers.legacy_game_history_handler import GameHistory
import hashlib


class _RemoveDuplicatesHelper(ndb.Model):
    hash = ndb.StringProperty()
    game_id = ndb.IntegerProperty()


class RemoveDuplicates(ServiceRequestHandler):
    game_id = None

    def handle_game(self, game):
        hasher = hashlib.md5()
        hasher.update(game.json_string)
        _RemoveDuplicatesHelper(hash=hasher.hexdigest(), game_id=game.key.id()).put_async()

    def remove_game(self, helper):
        if helper.game_id != self.game_id:
            ndb.Key(GameHistory, helper.game_id).delete_async()
        helper.key.delete_async()

    @ndb.toplevel
    def post(self):
        stage = self.request.get('stage')
        if stage in ('', 'map'):
            GameHistory.query().map(self.handle_game)
        elif stage == 'reduce':
            n = _RemoveDuplicatesHelper.query().get()
            if n is None:
                self.abort(200)
            self.game_id = n.game_id
            _RemoveDuplicatesHelper.query(_RemoveDuplicatesHelper.hash == n.hash).map(self.remove_game)
            taskqueue.add(url='/remove_duplicates',
                          params={'stage': 'reduce'},
                          queue_name='fast')

