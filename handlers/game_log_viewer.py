__author__ = 'nikolay'
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from google.appengine.ext import ndb
import json

class GameLogViewer(AdminRequestHandler):
    def get(self):
        key = self.request.get("key")
        game = None
        if key:
            game = ndb.Key(urlsafe=key).get()
            if game:
                if game.key.kind() == 'GameLog':
                    game = game.json
                elif game.key.kind() == 'GameHistory':
                    game = game.json_string
                else:
                    game = None
        if game:
            game = json.dumps(json.loads(game), indent=4, separators=(',', ': '), ensure_ascii=False)\
                .replace('\n', '<br>\n')\
                .replace(' ', '&nbsp;')
        self.draw_page('game_log_viewer', game=game)