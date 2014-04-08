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

import handlers
import handlers.dictionaries_packages_handlers
import handlers.dictionaries_packages_admin_handlers
import handlers.userdictionary
import handlers.log_n_res_handlers
import handlers.complain_word_handlers
import handlers.newsfeed_handlers
import handlers.assign_device_handler
import handlers.global_dictionary_word_handlers
import handlers.recalc_rating_handler
import handlers.web_game_creation_handler
import handlers.link_device
import handlers.statistics.word_statistics_handler
import handlers.statistics.update_mathplotlib_plots
import handlers.remove_duplicates
import handlers.admin_page_handler
import handlers.pregame_handlers
import handlers.statistics.total_statistics_handler
import handlers.frequency_dictionary_handlers
import handlers.game_log_viewer
import handlers.unknown_word_handler
import handlers.word_lookup
from handlers.base_handlers.web_request_handler import WebRequestHandler


class MainPage(WebRequestHandler):
    def get(self):
        self.draw_page('index')


routes = [
    webapp2.Route(r'/<device_id:[-\w]+>/api/linkdevice',
                  handler=handlers.link_device.LinkDevice,
                  name='linkdevice'),
    webapp2.Route(r'/internal/linkdevice',
                  handler=handlers.link_device.LinkDeviceMaintainConsistency,
                  name='internal_linkdevice'),

    #Unknown words handlers
    webapp2.Route(r'/admin/unknown_word/list',
                  handler=handlers.unknown_word_handler.GetWordPageHandler,
                  name='get unknown words list'),
    webapp2.Route(r'/admin/unknown_word/add',
                  handler=handlers.unknown_word_handler.AddWordHanler,
                  name='add word'),
    webapp2.Route(r'/admin/unknown_word/ignore',
                  handler=handlers.unknown_word_handler.IgnoreWordHanler,
                  name='ignore word'),

    #Frequency dictionary handlers
    webapp2.Route(r'/admin/frequency_dictionary/add',
                  handler=handlers.frequency_dictionary_handlers.MakeDictionaryHandler,
                  name='add dict'),
    webapp2.Route(r'/admin/frequency_dictionary/delete',
                  handler=handlers.frequency_dictionary_handlers.DeleteDictionary,
                  name='delete dict'),
    webapp2.Route(r'/internal/frequency_dictionary/delete/task_queue',
                  handler=handlers.frequency_dictionary_handlers.DeleteDictionaryTaskQueue,
                  name='delete dict'),
    webapp2.Route(r'/internal/frequency_dictionary/add/task_queue',
                  handler=handlers.frequency_dictionary_handlers.MakeDictionaryTaskQueueHandler,
                  name='add dict task_queue'),

    #Word lookup handlers
    webapp2.Route(r'/admin/word_lookup/add',
                  handler=handlers.word_lookup.AddLookups,
                  name="add_lookups"),

    #recalc rating & make_statistics handlers
    #web
    webapp2.Route(r'/admin/logs_processing',
                  handler=handlers.recalc_rating_handler.LogsAdminPage),
    webapp2.Route(r'/cron/update_plots/start/<admin:[-\w]*>',
                  handler=handlers.statistics.update_mathplotlib_plots.runUpdateAll),
    #service
    webapp2.Route(r'/internal/update_heatmap/task_queue',
                  handler=handlers.statistics.update_mathplotlib_plots.UpdateHeatMapTaskQueue,
                  name='update heatmap task queue'),
    webapp2.Route(r'/internal/update_scatter/task_queue',
                  handler=handlers.statistics.update_mathplotlib_plots.UpdateScatterPlotTaskQueue,
                  name='update heatmap task queue'),
    webapp2.Route(r'/internal/update_d/task_queue',
              handler=handlers.statistics.update_mathplotlib_plots.UpdateDPlotHeatMapTaskQueue,
              name='update d task queue'),
    webapp2.Route(r'/internal/recalc_rating_after_game',
                  handler=handlers.recalc_rating_handler.RecalcRatingHandler,
                  name='recalc_rating'),
    webapp2.Route(r'/internal/add_game_to_statistic',
                  handler=handlers.recalc_rating_handler.AddGameHandler,
                  name='add_game_Statistic'),
    webapp2.Route(r'/internal/recalc_all_logs',
                  handler=handlers.recalc_rating_handler.RecalcAllLogs),

    #User dictionary handlers
    (r'/html/udict/edit', handlers.userdictionary.DrawWebpage),
    (r'/html/udict/proc', handlers.userdictionary.ProcWebpage),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict/',
                  handler=handlers.userdictionary.UserDictionaryHandler,
                  name='udict_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict/since/<version:[-\w]+>',
                  handler=handlers.userdictionary.UserDictionaryHandler,
                  name='udict_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict',
                  handler=handlers.userdictionary.UserDictionaryHandler,
                  name='udict_get'),

    #Web handlers
    (r'/', MainPage),
    (r'/admin', handlers.admin_page_handler.AdminPage),
    webapp2.Route(r'/user/create_game',
                  handler=handlers.web_game_creation_handler.WebGameCreationHandler,
                  name='create_game'),
    webapp2.Route(r'/remove_duplicates',
                  handler=handlers.remove_duplicates.RemoveDuplicates,
                  name='remove_duplicates'),
    webapp2.Route(r'/images/scatter_plot/<N:[-\d]+>',
                  handler=handlers.statistics.total_statistics_handler.ScattedPlotHandler,
                  name='scatter_plot'),
    webapp2.Route(r'/images/heatmap_plot/<N:[-\d]+>',
                  handler=handlers.statistics.total_statistics_handler.HeatmapPlotHandler,
                  name='heatmap_plot'),
    webapp2.Route(r'/images/d_plot',
                  handler=handlers.statistics.total_statistics_handler.DPlotHandler,
                  name='d_plot'),


    #Statistics web handlers
    webapp2.Route(r'/statistics/word_statistics',
                  handler=handlers.statistics.word_statistics_handler.WordStatisticsHandler,
                  name='stats'),
    webapp2.Route('/statistics/total_statistics',
                  handler=handlers.statistics.total_statistics_handler.TotalStatisticsHandler,
                  name="total statistics handler"),
    webapp2.Route('/admin/view_game_log',
                  handler=handlers.game_log_viewer.GameLogViewer,
                  name='view_log'),
    webapp2.Route('/admin/ignore_game_log',
                  handler=handlers.game_log_viewer.IgnoreGameLogHandler,
                  name='ignore_log'),

    #gamelog handlers
    webapp2.Route(r'/<device_id:[-\w]+>/game_log',
                  handler=handlers.log_n_res_handlers.GameLogHandler,
                  name='upload_log'),
    #migration route: to be removed
    webapp2.Route(r'/<device_id:[-\w]+>/game_log/<game_id:[-\w]+>',
                  handler=handlers.log_n_res_handlers.GameLogHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/game_results/<game_id:[-\w]+>',
                  handler=handlers.log_n_res_handlers.GameResultsHandler,
                  name='upload_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/game_results/since/<timestamp:[-\w]+>',
                  handler=handlers.log_n_res_handlers.GameResultsUpdateHandler,
                  name='check_for_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/get_results/<game_id:[-\w]+>',
                  handler=handlers.log_n_res_handlers.GameResultsHandler,
                  name='get_results'),
    webapp2.Route(r'/save_game',
                  handler=handlers.log_n_res_handlers.SaveGameHandler,
                  name='save_game'),
    webapp2.Route(r'/save_game/<pin:[-\w]+>',
                  handler=handlers.log_n_res_handlers.SaveGameHandler,
                  name='load_game'),


    #Word streams handlers
    webapp2.Route(r'/admin/streams',
                  handler=handlers.dictionaries_packages_admin_handlers.AddStreamHandler,
                  name='edit_words'),
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
    webapp2.Route(r'/admin/streams/<stream_id:[-\w]+>/packages/add',
                  handler=handlers.dictionaries_packages_admin_handlers.AddPackageHandler,
                  name='add_package'),
    webapp2.Route(r'/admin/streams/packages/<package_id:[-\w]+>/words',
                  handler=handlers.dictionaries_packages_admin_handlers.ChangeWordsHandler,
                  name='change_words'),

    #Pregame handlers
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/create',
                  handler=handlers.pregame_handlers.PreGameCreateHandler,
                  name='pregame_create'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/join',
                  handler=handlers.pregame_handlers.PreGameJoinHandler,
                  name='pregame_join'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/get_current_game',
                  handler=handlers.pregame_handlers.PreGameCurrentHandler,
                  name='pregame_current'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>',
                  handler=handlers.pregame_handlers.PreGameHandler,
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

    #assign device handlers
    webapp2.Route(r'/<device_id:[-\w]+>/assign_device',
                  handler=handlers.assign_device_handler.AssignDeviceHandler,
                  name='assign_device'),

    #Newsfeed handlers
    webapp2.Route(r'/news/<id:[-\d]+>',
                  handler=handlers.newsfeed_handlers.ShowNewsHandler,
                  name="show news"),
    webapp2.Route(r'/news/login',
                  handler=handlers.newsfeed_handlers.LoginPageHandler,
                  name='login to news'),
    webapp2.Route(r'/news/add',
                  handler=handlers.newsfeed_handlers.AddNewsHandler,
                  name='add news'),
    webapp2.Route(r'/news/list',
                  handler=handlers.newsfeed_handlers.ListOfNewsHandler,
                  name="list of news"),
    webapp2.Route(r'/news/load/(\d+)',
                  handler=handlers.newsfeed_handlers.LoadNewsHandler,
                  name="show news"),

    #Complain words handlers
    #admin handlers
    webapp2.Route('/admin/complain/list',
                  handler=handlers.complain_word_handlers.ShowComplainedWords,
                  name='show_complained_words'),
    webapp2.Route('/admin/complain/clear',
                  handler=handlers.complain_word_handlers.DeleteComplainedWords,
                  name='delete_complained_words'),
    webapp2.Route('/admin/complain/cancel',
                  handler=handlers.complain_word_handlers.DeleteComplainedWord,
                  name='delete_current_complained_word'),
    webapp2.Route('/admin/complain/remove',
                  handler=handlers.complain_word_handlers.DeleteFromGlobalDictionaryHandler,
                  name='delete_from_global'),
    #Authorized api requests
    webapp2.Route(r'/<device_id:[-\w]+>/complain',
                  handler=handlers.complain_word_handlers.ComplainWordHandler,
                  name='complain_word'),

    #GlobalDictionary handlers
    #admin handlers
    webapp2.Route(r'/admin/global_dictionary/add_words',
                  handler=handlers.global_dictionary_word_handlers.WordsAddHandler,
                  name='add words to global'),
    webapp2.Route(r'/admin/global_dictionary/delete',
                  handler=handlers.global_dictionary_word_handlers.DeleteDictionary,
                  name='delete'),
    webapp2.Route(r'/internal/global_dictionary/delete/task_queue',
                  handler=handlers.global_dictionary_word_handlers.DeleteDictionaryTaskQueue,
                  name='delete task_queue'),
    webapp2.Route(r'/admin/global_dictionary/update_json',
                  handler=handlers.global_dictionary_word_handlers.UpdateJsonHandler,
                  name='update json'),
    webapp2.Route(r'/admin/global_dictionary/update_json/all',
                  handler=handlers.global_dictionary_word_handlers.UpdateAllJsonsHandler,
                  name="update all jsons"),
    #api handlers
    webapp2.Route(r'/api/global_dictionary/get_words/<timestamp:[-\d]+>',
                  handler=handlers.global_dictionary_word_handlers.GlobalDictionaryGetWordsHandler,
                  name='get words'),
    #service handlers
    webapp2.Route(r'/internal/global_dictionary/add_words/task_queue',
                  handler=handlers.global_dictionary_word_handlers.TaskQueueAddWords,
                  name='add words to global task queue'),
    webapp2.Route(r'/internal/global_dictionary/update_json/task_queue',
                  handler=handlers.global_dictionary_word_handlers.TaskQueueUpdateJson,
                  name='update json task queue')


]

app = webapp2.WSGIApplication(routes, debug=True)