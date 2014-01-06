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

import pregame_handlers
import dictionaries_packages_handlers
import dictionaries_packages_admin_handlers
import userdictionary
import log_n_res_handlers
import complain_word_handlers
import newsfeed_handlers
import assign_device_handler
import global_dictionary_word_handlers
import recalc_rating_handler
import constants.constants


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello, first handler!')


routes = [
    (r'/', MainHandler),
    webapp2.Route(
        constants.constants.delete_all_url,
        handler=complain_word_handlers.DeleteComplainedWords,
        name='delete_complained_words'),
    webapp2.Route(
        constants.constants.delete_current_url,
        handler=complain_word_handlers.DeleteComplainedWord,
        name='delete_current_complained_word'),
    webapp2.Route(
        constants.constants.show_complained_url,
        handler=complain_word_handlers.ShowComplainedWords,
        name='show_complained_words'),
    webapp2.Route(
        constants.constants.delete_from_global_url,
        handler=complain_word_handlers.DeleteFromGlobalDictionaryHandler,
        name='delete_from_global'
    ),
    webapp2.Route(r'/edit_words',
                  handler=global_dictionary_word_handlers.GlobalWordEditor,
                  name='edit_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/complain',
                  handler=complain_word_handlers.ComplainWordHandler,
                  name='complain_word'),
    webapp2.Route(r'/<device_id:[-\w]+>/get_all_words/<version:[-\w]+>',
                  handler=global_dictionary_word_handlers.GlobalDictionaryWordHandler,
                  name='get_all_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/create',
                  handler=pregame_handlers.PreGameCreateHandler,
                  name='pregame_create'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/join', handler=pregame_handlers.PreGameJoinHandler,
                  name='pregame_join'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/get_current_game', handler=pregame_handlers.PreGameCurrentHandler,
                  name='pregame_current'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>', handler=pregame_handlers.PreGameHandler,
                  name='pregame_get'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/update',
                  handler=pregame_handlers.PreGameUpdateHandler,
                  name='pregame_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/version',
                  handler=pregame_handlers.PreGameVersionHandler,
                  name='pregame_version'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>'
                  r'/since/<version:[\d]+>',
                  handler=pregame_handlers.PreGameSinceHandler,
                  name='pregame_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/start',
                  handler=pregame_handlers.PreGameStartHandler,
                  name='pregame_start'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/abort',
                  handler=pregame_handlers.PreGameAbortHandler,
                  name='pregame_abort'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams', handler=dictionaries_packages_handlers.GetStreamsListHandler,
                  name='stream_list'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/<stream_id:[-\w]+>'
                  r'/to/<on:(true)|(false)>',
                  handler=dictionaries_packages_handlers.ChangeStreamStateHandler,
                  name='change_stream_state'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/<stream_id:[-\w]+>',
                  handler=dictionaries_packages_handlers.GetPackagesListHandler,
                  name='package_list'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/packages/<package_id:[-\w]+>',
                  handler=dictionaries_packages_handlers.GetPackageHandler,
                  name='get_package'),
    webapp2.Route(r'/streams',
                  handler=dictionaries_packages_admin_handlers.AddStreamHandler,
                  name='add_stream'),
    webapp2.Route(
        r'/streams/<stream_id:[-\w]+>/packages/add',
        handler=dictionaries_packages_admin_handlers.AddPackageHandler,
        name='add_package'),
    webapp2.Route(r'/streams/packages/<package_id:[-\w]+>/words',
                  handler=dictionaries_packages_admin_handlers.ChangeWordsHandler,
                  name='change_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/upload_log/<game_id:[-\w]+>', handler=log_n_res_handlers.UploadLog,
                  name='upload_log'),
    webapp2.Route(r'/<device_id:[-\w]+>/upload_results/<game_id:[-\w]+>', handler=log_n_res_handlers.UploadRes,
                  name='upload_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/check_for_results/<timestamp:[-\w]+>',
                  handler=log_n_res_handlers.CheckAnyResults,
                  name='check_for_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/get_results/<game_id:[-\w]+>', handler=log_n_res_handlers.GetResults,
                  name='get_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/udict/update',
                  handler=userdictionary.Change,
                  name='udict_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/udict/get/since/<version:[-\w]+>',
                  handler=userdictionary.Update,
                  name='udict_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/udict/get',
                  handler=userdictionary.Get,
                  name='udict_get'),
    (r'/html/udict/edit', userdictionary.DrawWebpage),
    (r'/html/udict/proc', userdictionary.ProcWebpage),
    (r'/login', newsfeed_handlers.LoginPageHandler), # News Feed starts here
    (r'/addnews', newsfeed_handlers.AddNewsHandler),
    (r'/news/(\d+)', newsfeed_handlers.ShowNewsHandler),
    (r'/listofnews', newsfeed_handlers.ListOfNewsHandler),
    (r'/loadnews/(\d+)', newsfeed_handlers.LoadNewsHandler), # News Feed finishes here
    (r'/generate_pin', assign_device_handler.GeneratePinHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/assign_device',
                  handler=assign_device_handler.AssignDeviceHandler,
                  name='assign_device'),
    webapp2.Route(r'/internal/recalc_rating_after_game',
                  handler=recalc_rating_handler.RecalcRatingHandler,
                  name='recalc_rating'),
    webapp2.Route(r'/internal/add_game_to_statistic',
                  handler=recalc_rating_handler.AddGameHandler,
                  name='add_game_Statistic'),
    webapp2.Route(r'/json_updater',
                  handler=global_dictionary_word_handlers.dictionary_updater,
                  name='json_updater'
    )
]
app = webapp2.WSGIApplication(routes, debug=True)
