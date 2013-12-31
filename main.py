#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import pregame_handlers, dictionaries_packages, userdictionary, results_handlers, complain_word_handlers


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello, first handler!')

routes = [
    (r'/', MainHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/complain', handler=complain_word_handlers.ComplainWordHandler,
                  name='complain'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/create', handler=pregame_handlers.PreGameCreateHandler,
                  name='pregame_create'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>', handler=pregame_handlers.PreGameHandler,
                  name='pregame_get'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/update', handler=pregame_handlers.PreGameUpdateHandler,
                  name='pregame_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/version',
                  handler=pregame_handlers.PreGameVersionHandler, name='pregame_version'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/since/<version:[\d]+>',
                  handler=pregame_handlers.PreGameSinceHandler, name='pregame_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/start', handler=pregame_handlers.PreGameStartHandler,
                  name='pregame_start'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/abort', handler=pregame_handlers.PreGameAbortHandler,
                  name='pregame_abort'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/join', handler=pregame_handlers.PreGameJoinHandler,
                  name='pregame_join'),
    (r'/streams', dictionaries_packages.GetStreamsListHandler),
    (r'/streams/([-\w]+)/to/([-\w]+)', dictionaries_packages.ChangeStreamStateHandler),
    (r'/streams/([-\w]+)', dictionaries_packages.GetPackagesListHandler),
    (r'/streams/packages/([-\w]+)', dictionaries_packages.GetPackageHandler),
    (r'/udict/([-\w]+)/change/', userdictionary.Change),
    (r'/udict/([-\w]+)/update/([-\w]+)', userdictionary.Update),
    (r'/results/([-\w]+)', results_handlers.ResultsHandler)
]

app = webapp2.WSGIApplication(routes, debug=True)
