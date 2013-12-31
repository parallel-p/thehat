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
import pregame_handlers, dictionaries_packages, userdictionary, results_handlers


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello, first handler!')


class SecondHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello, second handler!')

routes = [
    (r'/', MainHandler),
    (r'/second/', SecondHandler),
    (r'/pregame/new', pregame_handlers.PreGameNewHandler),
    (r'/pregame/([-\w]+)', pregame_handlers.PreGameHandler),
    (r'/pregame/([-\w]+)/update', pregame_handlers.PreGameUpdateHandler),
    (r'/pregame/([-\w]+)/version', pregame_handlers.PreGameVersionHandler),
    (r'/pregame/([-\w]+)/since/([\d]+)', pregame_handlers.PreGameSinceHandler),
    (r'/pregame/([-\w]+)/start', pregame_handlers.PreGameStartHandler),
    (r'/pregame/([-\w]+)/abort', pregame_handlers.PreGameAbortHandler),
    (r'/pregame/join', pregame_handlers.PreGameJoinHandler),
    (r'/streams', dictionaries_packages.GetStreamsListHandler),
    (r'/streams/([-\w]+)/to/([-\w]+)', dictionaries_packages.ChangeStreamStateHandler),
    (r'/streams/([-\w]+)', dictionaries_packages.GetPackagesListHandler),
    (r'/streams/packages/([-\w]+)', dictionaries_packages.GetPackageHandler),
    (r'/udict/change/', userdictionary.Change),
    (r'/udict/update/', userdictionary.Update),
    (r'/results/([-\w]+)', results_handlers.ResultsHandler)
]

app = webapp2.WSGIApplication(routes, debug=True)
