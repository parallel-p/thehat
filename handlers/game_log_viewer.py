from handlers import AdminRequestHandler

__author__ = 'nikolay'
from google.appengine.ext import ndb
import json


class GameLogViewer(AdminRequestHandler):
    def get(self):
        key = self.request.get("key")
        game, game_string = None, None
        if key:
            game = ndb.Key(urlsafe=key).get()
            if game:
                if game.key.kind() == 'GameLog':
                    game_string = game.json
                elif game.key.kind() == 'GameHistory':
                    game_string = game.json_string
        if game_string:
            game_string = json.dumps(json.loads(game_string), indent=4, separators=(',', ': '), ensure_ascii=False)\
                .replace('\n', '<br>\n')\
                .replace(' ', '&nbsp;')
        self.draw_page('game_log_viewer', key=key, game_string=game_string, game=game)


class IgnoreGameLogHandler(AdminRequestHandler):
    def get(self):
        key = self.request.get("key")
        game = ndb.Key(urlsafe=key).get()
        if game:
            game.ignored = not game.ignored
            if game.ignored:
                game.reason = 'manual'
            game.put()
        self.redirect("/admin/view_game_log?key={}".format(key))