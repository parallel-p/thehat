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
from webapp2 import Route

import handlers.admin_page
import handlers.dictionary_packages
import handlers.dictionary_packages.admin
import handlers.game_log_viewer
import handlers.global_dictionary.complain_word
import handlers.global_dictionary.frequency
import handlers.global_dictionary.word_lookup
import handlers.global_dictionary.words
import handlers.link_device
import handlers.log_saving
import handlers.newsfeed
import handlers.pregame
import handlers.service.notifications
import handlers.service.remove_duplicates
import handlers.statistics.calculation
import handlers.statistics.functions
import handlers.statistics.game_len_prediction
import handlers.statistics.plots
import handlers.statistics.total
import handlers.statistics.word
import handlers.user_dictionary
import handlers.user_properies
import handlers.user_settings
import handlers.web_game_creation
from handlers import WebRequestHandler


class MainPage(WebRequestHandler):
    def get(self):
        self.draw_page('index')


routes = [

    #user handlers
    webapp2.Route(r'/user/settings',
                  handler=handlers.user_settings.UserSettingsHandler,
                  name='user settings'),

    #notification handlers
    webapp2.Route(r'/cron/notifications/update',
                  handler=handlers.service.notifications.MakeChannelHandler,
                  name='send notification'),
    webapp2.Route(r'/admin/notifications/send',
                  handler=handlers.service.notifications.NotificationHandler,
                  name='send notification'),

    #prediction handlers
    webapp2.Route(r'/admin/statistics/prediction',
                  handler=handlers.statistics.game_len_prediction.GameLenPredictionHandler,
                  name='prediction'),


    webapp2.Route(r'/<device_id:[-\w]+>/api/linkdevice',
                  handler=handlers.link_device.LinkDevice,
                  name='linkdevice'),
    webapp2.Route(r'/internal/linkdevice',
                  handler=handlers.link_device.LinkDeviceMaintainConsistency,
                  name='internal_linkdevice'),

    #function statistics handler
    webapp2.Route(r'/admin/statistics/functions/add',
                  handler=handlers.statistics.functions.AddFunctionHandler,
                  name='add function'),
    webapp2.Route(r'/admin/statistics/functions/update',
                  handler=handlers.statistics.functions.UpdateFunctionsStatisticsHandler,
                  name='update stat'),
    webapp2.Route(r'/cron/statistics/functions/update',
                  handler=handlers.statistics.functions.CronUpdateResHandlers,
                  name='update stat cron'),
    webapp2.Route(r'/internal/statistics/functions/update/task_queue',
                  handler=handlers.statistics.functions.UpdateFunctionsStatisticsHandlerTaskQueue,
                  name='update stat'),
    webapp2.Route(r'/admin/statistics/functions/show',
                  handler=handlers.statistics.functions.ResultShowHandler,
                  name='push results'),

    #User api request handlers
    #user
    webapp2.Route(r'/api/settings/user/get/all',
                  handler=handlers.user_properies.GetAllValues.User,
                  name='get all values'),
    webapp2.Route(r'/api/settings/user/update',
                  handler=handlers.user_properies.UpdateValues.User,
                  name='get all values'),
    webapp2.Route(r'/api/settings/user/delete',
                  handler=handlers.user_properies.DeleteValues.User,
                  name='delete values'),
    webapp2.Route(r'/api/settings/user/version',
                  handler=handlers.user_properies.GetLastUserVersion,
                  name='get version'),
    #this device
    webapp2.Route(r'/api/settings/device/get/all',
                  handler=handlers.user_properies.GetAllValues.Device,
                  name='get all values'),
    webapp2.Route(r'/api/settings/device/update',
                  handler=handlers.user_properies.UpdateValues.Device,
                  name='get all values'),
    webapp2.Route(r'/api/settings/device/delete',
                  handler=handlers.user_properies.DeleteValues.Device,
                  name='delete values'),
    webapp2.Route(r'/api/settings/device/version',
                  handler=handlers.user_properies.GetLastDeviceVersion,
                  name='get version'),
    #devices
    webapp2.Route(r'/api/settings/user_devices/get/all',
                  handler=handlers.user_properies.GetAllValues.Devices,
                  name='get all values'),
    webapp2.Route(r'/api/settings/user_devices/update',
                  handler=handlers.user_properies.UpdateValues.Devices,
                  name='get all values'),
    webapp2.Route(r'/api/settings/user_devices/delete',
                  handler=handlers.user_properies.DeleteValues.Devices,
                  name='delete values'),
    webapp2.Route(r'/api/settings/user_devices/version',
                  handler=handlers.user_properies.GetLastDevicesVersion,
                  name='get version'),
    #end api andlers

    #Unknown words handlers
    webapp2.Route(r'/admin/unknown_word/list',
                  handler=handlers.global_dictionary.unknown_words.GetWordPageHandler,
                  name='get unknown words list'),
    webapp2.Route(r'/admin/unknown_word/add',
                  handler=handlers.global_dictionary.unknown_words.AddWordHanler,
                  name='add word'),
    webapp2.Route(r'/admin/unknown_word/ignore',
                  handler=handlers.global_dictionary.unknown_words.IgnoreWordHanler,
                  name='ignore word'),

    #Frequency dictionary handlers
    webapp2.Route(r'/admin/frequency_dictionary/add',
                  handler=handlers.global_dictionary.frequency.MakeDictionaryHandler,
                  name='add dict'),
    webapp2.Route(r'/admin/frequency_dictionary/delete',
                  handler=handlers.global_dictionary.frequency.DeleteDictionary,
                  name='delete dict'),
    webapp2.Route(r'/internal/frequency_dictionary/delete/task_queue',
                  handler=handlers.global_dictionary.frequency.DeleteDictionaryTaskQueue,
                  name='delete dict'),
    webapp2.Route(r'/internal/frequency_dictionary/add/task_queue',
                  handler=handlers.global_dictionary.frequency.MakeDictionaryTaskQueueHandler,
                  name='add dict task_queue'),

    #Word lookup handlers
    webapp2.Route(r'/admin/word_lookup/add',
                  handler=handlers.global_dictionary.word_lookup.AddLookups,
                  name="add_lookups"),

    #recalc rating & make_statistics handlers
    #web
    webapp2.Route(r'/admin/operations',
                  handler=handlers.operations_admin_page.OperationsAdminPage),
    webapp2.Route(r'/cron/update_plots/start/<admin:[-\w]*>',
                  handler=handlers.statistics.plots.runUpdateAll),
    #service
    webapp2.Route(r'/internal/update_heatmap/task_queue',
                  handler=handlers.statistics.plots.UpdateHeatMapTaskQueue,
                  name='update heatmap task queue'),
    webapp2.Route(r'/internal/update_scatter/task_queue',
                  handler=handlers.statistics.plots.UpdateScatterPlotTaskQueue,
                  name='update heatmap task queue'),
    webapp2.Route(r'/internal/update_d/task_queue',
                  handler=handlers.statistics.plots.UpdateDPlotHeatMapTaskQueue,
                  name='update d task queue'),
    webapp2.Route(r'/internal/add_game_to_statistic',
                  handler=handlers.statistics.calculation.AddGameHandler,
                  name='add_game_Statistic'),
    webapp2.Route(r'/internal/recalc_all_logs',
                  handler=handlers.statistics.calculation.RecalcAllLogs),

    #User dictionary handlers
    (r'/html/udict/edit', handlers.user_dictionary.DrawWebpage),
    (r'/html/udict/proc', handlers.user_dictionary.ProcWebpage),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict/',
                  handler=handlers.user_dictionary.UserDictionaryHandler,
                  name='udict_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict/since/<version:[-\w]+>',
                  handler=handlers.user_dictionary.UserDictionaryHandler,
                  name='udict_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/api/udict',
                  handler=handlers.user_dictionary.UserDictionaryHandler,
                  name='udict_get'),

    #Web handlers
    (r'/', MainPage),
    (r'/admin', handlers.admin_page.AdminPage),
    webapp2.Route(r'/user/create_game',
                  handler=handlers.web_game_creation.WebGameCreationHandler,
                  name='create_game'),
    webapp2.Route(r'/remove_duplicates',
                  handler=handlers.service.remove_duplicates.RemoveDuplicates,
                  name='remove_duplicates'),
    webapp2.Route(r'/images/scatter_plot/<N:[-\d]+>',
                  handler=handlers.statistics.total.ScattedPlotHandler,
                  name='scatter_plot'),
    webapp2.Route(r'/images/heatmap_plot/<N:[-\d]+>',
                  handler=handlers.statistics.total.HeatmapPlotHandler,
                  name='heatmap_plot'),
    webapp2.Route(r'/images/d_plot',
                  handler=handlers.statistics.total.DPlotHandler,
                  name='d_plot'),


    #Statistics web handlers
    webapp2.Route(r'/statistics/word_statistics',
                  handler=handlers.statistics.word.WordStatisticsHandler,
                  name='stats'),
    webapp2.Route('/statistics/total_statistics',
                  handler=handlers.statistics.total.TotalStatisticsHandler,
                  name="total statistics handler"),
    webapp2.Route('/admin/view_game_log',
                  handler=handlers.game_log_viewer.GameLogViewer,
                  name='view_log'),
    webapp2.Route('/admin/ignore_game_log',
                  handler=handlers.game_log_viewer.IgnoreGameLogHandler,
                  name='ignore_log'),

    #gamelog handlers
    webapp2.Route(r'/<device_id:[-\w]+>/game_log',
                  handler=handlers.log_saving.GameLogHandler,
                  name='upload_log'),
    #migration route: to be removed
    webapp2.Route(r'/<device_id:[-\w]+>/game_log/<game_id:[-\w]+>',
                  handler=handlers.log_saving.GameLogHandler),
    webapp2.Route(r'/<device_id:[-\w]+>/game_results/<game_id:[-\w]+>',
                  handler=handlers.log_saving.GameResultsHandler,
                  name='upload_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/game_results/since/<timestamp:[-\w]+>',
                  handler=handlers.log_saving.GameResultsUpdateHandler,
                  name='check_for_results'),
    webapp2.Route(r'/<device_id:[-\w]+>/get_results/<game_id:[-\w]+>',
                  handler=handlers.log_saving.GameResultsHandler,
                  name='get_results'),
    webapp2.Route(r'/save_game',
                  handler=handlers.log_saving.SaveGameHandler,
                  name='save_game'),
    webapp2.Route(r'/save_game/<pin:[-\w]+>',
                  handler=handlers.log_saving.SaveGameHandler,
                  name='load_game'),


    #Word streams handlers
    webapp2.Route(r'/admin/streams',
                  handler=handlers.dictionary_packages.admin.AddStreamHandler,
                  name='edit_words'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams', handler=handlers.dictionary_packages.GetStreamsListHandler,
                  name='stream_list'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/<stream_id:[-\w]+>'
                  r'/to/<on:(true)|(false)>',
                  handler=handlers.dictionary_packages.ChangeStreamStateHandler,
                  name='change_stream_state'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/<stream_id:[-\w]+>',
                  handler=handlers.dictionary_packages.GetPackagesListHandler,
                  name='package_list'),
    webapp2.Route(r'/<device_id:[-\w]+>/streams/packages/<package_id:[-\w]+>',
                  handler=handlers.dictionary_packages.GetPackageHandler,
                  name='get_package'),
    webapp2.Route(r'/admin/streams/<stream_id:[-\w]+>/packages/add',
                  handler=handlers.dictionary_packages.admin.AddPackageHandler,
                  name='add_package'),
    webapp2.Route(r'/admin/streams/packages/<package_id:[-\w]+>/words',
                  handler=handlers.dictionary_packages.admin.ChangeWordsHandler,
                  name='change_words'),

    #Pregame handlers
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/create',
                  handler=handlers.pregame.PreGameCreateHandler,
                  name='pregame_create'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/join',
                  handler=handlers.pregame.PreGameJoinHandler,
                  name='pregame_join'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/get_current_game',
                  handler=handlers.pregame.PreGameCurrentHandler,
                  name='pregame_current'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>',
                  handler=handlers.pregame.PreGameHandler,
                  name='pregame_get'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/update',
                  handler=handlers.pregame.PreGameUpdateHandler,
                  name='pregame_update'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/version',
                  handler=handlers.pregame.PreGameVersionHandler,
                  name='pregame_version'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>'
                  r'/since/<version:[\d]+>',
                  handler=handlers.pregame.PreGameSinceHandler,
                  name='pregame_since'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/start',
                  handler=handlers.pregame.PreGameStartHandler,
                  name='pregame_start'),
    webapp2.Route(r'/<device_id:[-\w]+>/pregame/<game_id:[-\w]+>/abort',
                  handler=handlers.pregame.PreGameAbortHandler,
                  name='pregame_abort'),

    #Newsfeed handlers
    webapp2.Route(r'/news/<id:[-\d]+>',
                  handler=handlers.newsfeed.ShowNewsHandler,
                  name="show news"),
    webapp2.Route(r'/news/login',
                  handler=handlers.newsfeed.LoginPageHandler,
                  name='login to news'),
    webapp2.Route(r'/news/add',
                  handler=handlers.newsfeed.AddNewsHandler,
                  name='add news'),
    webapp2.Route(r'/news/list',
                  handler=handlers.newsfeed.ListOfNewsHandler,
                  name="list of news"),
    webapp2.Route(r'/news/load/(\d+)',
                  handler=handlers.newsfeed.LoadNewsHandler,
                  name="show news"),

    #Complain words handlers
    #admin handlers
    webapp2.Route('/admin/complain/list',
                  handler=handlers.global_dictionary.complain_word.ShowComplainedWords,
                  name='show_complained_words'),
    webapp2.Route('/admin/complain/clear',
                  handler=handlers.global_dictionary.complain_word.DeleteComplainedWords,
                  name='delete_complained_words'),
    webapp2.Route('/admin/complain/cancel',
                  handler=handlers.global_dictionary.complain_word.DeleteComplainedWord,
                  name='delete_current_complained_word'),
    webapp2.Route('/admin/complain/postpone',
                  handler=handlers.global_dictionary.complain_word.PostponeComplainedWord,
                  name='postpone'),
    webapp2.Route('/admin/complain/remove',
                  handler=handlers.global_dictionary.complain_word.DeleteFromGlobalDictionaryHandler,
                  name='delete_from_global'),
    #Authorized api requests
    webapp2.Route(r'/<device_id:[-\w]+>/complain',
                  handler=handlers.global_dictionary.complain_word.ComplainWordHandler,
                  name='complain_word'),

    #GlobalDictionary handlers
    #admin handlers
    webapp2.Route(r'/admin/global_dictionary/add_words',
                  handler=handlers.global_dictionary.words.WordsAddHandler,
                  name='add words to global'),
    #service handlers
    webapp2.Route(r'/service/generate_dictionary',
                  handler=handlers.global_dictionary.words.GenerateDictionary),
    webapp2.Route(r'/internal/global_dictionary/add_words/task_queue',
                  handler=handlers.global_dictionary.words.TaskQueueAddWords,
                  name='add words to global task queue'),
]

api_v2_routes = [
        Route(r'/api/v2/dictionary/<lang:[-\w]+>',
              handler=handlers.global_dictionary.words.DictionaryHandler),
        Route(r'/api/v2/dictionary',
              handler=handlers.global_dictionary.words.DictionaryHandler),
        Route(r'/api/v2/dictionaries',
              handler=handlers.global_dictionary.words.ListDictionaries),
    Route(r'api/v2/game/log',
          handler=handlers.handlers.log_saving.GameLog2Handler)
]

config = {
    'webapp2_extras.jinja2': {
        'template_path': 'templates',
        'environment_args': {
            'extensions': ['jinja2.ext.i18n', 'jinja2.ext.autoescape']
        }
    }
}

app = webapp2.WSGIApplication(routes+api_v2_routes, debug=True, config=config)
