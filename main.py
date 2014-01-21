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

import handlers.pregame_handlers
import handlers.dictionaries_packages_handlers
import handlers.dictionaries_packages_admin_handlers
import handlers.userdictionary
import handlers.log_n_res_handlers
import handlers.complain_word_handlers
import handlers.newsfeed_handlers
import handlers.assign_device_handler
import handlers.global_dictionary_word_handlers
import handlers.recalc_rating_handler
import constants.constants
from environment import JINJA_ENVIRONMENT
import handlers.admin_page_handler
from google.appengine.api import users


class MainPage(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        if users.get_current_user():
            self.response.write(template.render(
                {"logout_link": users.create_logout_url('/')}))
        else:
            self.response.write(template.render({"login_link": users.create_login_url('/')}))



routes = [
    (r'/', MainPage),
    (r'/admin', handlers.admin_page_handler.AdminPage),
    webapp2.Route(
        constants.constants.delete_all_url,
        handler=handlers.complain_word_handlers.DeleteComplainedWords,
        name='delete_complained_words'),
    webapp2.Route(
        constants.constants.delete_current_url,
        handler=handlers.complain_word_handlers.DeleteComplainedWord,
        name='delete_current_complained_word'),
    webapp2.Route(
        constants.constants.show_complained_url,
        handler=handlers.complain_word_handlers.ShowComplainedWords,
        name='show_complained_words'),
    webapp2.Route(
        constants.constants.delete_from_global_url,
        handler=handlers.complain_word_handlers.DeleteFromGlobalDictionaryHandler,
        name='delete_from_global'
    ),
    webapp2.Route(r'/edit_words',
                  handler=handlers.global_dictionary_word_handlers.GlobalWordEditor,
                  name='edit_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/complain',
                  handler=handlers.complain_word_handlers.ComplainWordHandler,
                  name='complain_word'),
    webapp2.Route(r'/get_all_words/<version:[-\w]+>',
                  handler=handlers.global_dictionary_word_handlers.GlobalDictionaryWordHandler,
                  name='get_all_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/create',
                  handler=handlers.pregame_handlers.PreGameCreateHandler,
                  name='pregame_create'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/join', handler=handlers.pregame_handlers.PreGameJoinHandler,
                  name='pregame_join'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/get_current_game', handler=handlers.pregame_handlers.PreGameCurrentHandler,
                  name='pregame_current'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>', handler=handlers.pregame_handlers.PreGameHandler,
                  name='pregame_get'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/update',
                  handler=handlers.pregame_handlers.PreGameUpdateHandler,
                  name='pregame_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/version',
                  handler=handlers.pregame_handlers.PreGameVersionHandler,
                  name='pregame_version'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>'
                  r'/since/<version:[\d]+>',
                  handler=handlers.pregame_handlers.PreGameSinceHandler,
                  name='pregame_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/start',
                  handler=handlers.pregame_handlers.PreGameStartHandler,
                  name='pregame_start'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/abort',
                  handler=handlers.pregame_handlers.PreGameAbortHandler,
                  name='pregame_abort'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams', handler=handlers.dictionaries_packages_handlers.GetStreamsListHandler,
                  name='stream_list'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/<stream_id:[-\w]+>'
                  r'/to/<on:(true)|(false)>',
                  handler=handlers.dictionaries_packages_handlers.ChangeStreamStateHandler,
                  name='change_stream_state'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/<stream_id:[-\w]+>',
                  handler=handlers.dictionaries_packages_handlers.GetPackagesListHandler,
                  name='package_list'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/packages/<package_id:[-\w]+>',
                  handler=handlers.dictionaries_packages_handlers.GetPackageHandler,
                  name='get_package'),
    webapp2.Route(r'/streams',
                  handler=handlers.dictionaries_packages_admin_handlers.AddStreamHandler,
                  name='add_stream'),
    webapp2.Route(
        r'/streams/<stream_id:[-\w]+>/packages/add',
        handler=handlers.dictionaries_packages_admin_handlers.AddPackageHandler,
        name='add_package'),
    webapp2.Route(r'/streams/packages/<package_id:[-\w]+>/words',
                  handler=handlers.dictionaries_packages_admin_handlers.ChangeWordsHandler,
                  name='change_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/upload_log/<game_id:[-\w]+>', handler=handlers.log_n_res_handlers.UploadLog,
                  name='upload_log'),
    webapp2.Route(r'/<device_id:[-\w]+>/upload_results/<game_id:[-\w]+>', handler=handlers.log_n_res_handlers.UploadRes,
                  name='upload_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/check_for_results/<timestamp:[-\w]+>',
                  handler=handlers.log_n_res_handlers.CheckAnyResults,
                  name='check_for_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/get_results/<game_id:[-\w]+>', handler=handlers.log_n_res_handlers.GetResults,
                  name='get_results'),
    webapp2.Route(
        r'/<device_id:[-\w]+>/save_game/<game_id:[-\w]+>',
        handler=handlers.log_n_res_handlers.SaveGame, name='save_game'),
    webapp2.Route(
        r'/<device_id:[-\w]+>/load_game/<game_id:[-\w]+>',
        handler=handlers.log_n_res_handlers.LoadGame, name='load_game'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict/',
                  handler=handlers.userdictionary.UserDictionaryHandler,
                  name='udict_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict/since/<version:[-\w]+>',
                  handler=handlers.userdictionary.UserDictionaryHandler,
                  name='udict_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict',
                  handler=handlers.userdictionary.UserDictionaryHandler,
                  name='udict_get'),
    (r'/html/udict/edit', handlers.userdictionary.DrawWebpage),
    (r'/html/udict/proc', handlers.userdictionary.ProcWebpage),
    (r'/login', handlers.newsfeed_handlers.LoginPageHandler), # News Feed starts here
    (r'/addnews', handlers.newsfeed_handlers.AddNewsHandler),
    (r'/news/(\d+)', handlers.newsfeed_handlers.ShowNewsHandler),
    (r'/listofnews', handlers.newsfeed_handlers.ListOfNewsHandler),
    (r'/loadnews/(\d+)', handlers.newsfeed_handlers.LoadNewsHandler), # News Feed finishes here
    webapp2.Route(r'/internal/recalc_rating_after_game',
                  handler=handlers.recalc_rating_handler.RecalcRatingHandler,
                  name='recalc_rating'),
    webapp2.Route(r'/internal/add_game_to_statistic',
                  handler=handlers.recalc_rating_handler.AddGameHandler,
                  name='add_game_Statistic'),
    webapp2.Route(r'/json_updater',
                  handler=handlers.global_dictionary_word_handlers.dictionary_updater,
                  name='json_updater')
] + handlers.assign_device_handler.assign_device_routes

app = webapp2.WSGIApplication(routes, debug=True)
