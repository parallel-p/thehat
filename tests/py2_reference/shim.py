# -*- coding: utf-8 -*-
"""Fake App Engine modules so the *original* python27 statistics code can run.

Runs under python 2.7 only. The point is to execute
``legacy/handlers/statistics/calculation.py`` verbatim -- not a re-typed copy --
so that the python3 port in :mod:`app.stats` can be diffed against the code that
is actually in production.

Everything that touches Datastore, memcache or the task queue is stubbed; the
runner overrides the handler's write methods and records their arguments
instead.
"""

import sys
import types


class FakeKey(object):
    """Stand-in for ``ndb.Key``. The runner installs the entity to return."""

    current_entity = None

    def __init__(self, *args, **kwargs):
        self.urlsafe_value = kwargs.get('urlsafe', 'fake-urlsafe')
        self._kind = 'GameLog'
        self._id = getattr(FakeKey.current_entity, 'entity_id', 'fake-id')

    def kind(self):
        return self._kind

    def id(self):
        return self._id

    def get(self):
        return FakeKey.current_entity

    def urlsafe(self):
        return self.urlsafe_value


class FakeProperty(object):
    def __init__(self, *args, **kwargs):
        pass


class FakeModel(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def put(self):
        return FakeKey()

    @classmethod
    def query(cls, *args, **kwargs):
        raise NotImplementedError("the reference runner must not query")


def _identity_decorator(*args, **kwargs):
    """Works both as ``@dec`` and ``@dec(...)``."""
    if len(args) == 1 and not kwargs and callable(args[0]):
        return args[0]

    def wrap(func):
        return func

    return wrap


def _module(name):
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def install():
    # -- google.appengine ---------------------------------------------------
    google = sys.modules.get('google') or _module('google')
    appengine = _module('google.appengine')
    google.appengine = appengine
    api = _module('google.appengine.api')
    ext = _module('google.appengine.ext')
    appengine.api = api
    appengine.ext = ext

    taskqueue = _module('google.appengine.api.taskqueue')
    taskqueue.add = lambda *a, **kw: None
    taskqueue.Task = lambda *a, **kw: None
    taskqueue.Queue = lambda *a, **kw: None
    api.taskqueue = taskqueue

    memcache = _module('google.appengine.api.memcache')
    memcache.get = lambda *a, **kw: None
    memcache.set = lambda *a, **kw: None
    memcache.delete_multi = lambda *a, **kw: None
    api.memcache = memcache

    ndb = _module('google.appengine.ext.ndb')
    ndb.Model = FakeModel
    ndb.Key = FakeKey
    ndb.Cursor = FakeProperty
    ndb.Query = FakeProperty
    ndb.transactional = _identity_decorator
    ndb.toplevel = _identity_decorator
    ndb.tasklet = _identity_decorator
    ndb.delete_multi = lambda *a, **kw: None
    ndb.gql = lambda *a, **kw: []
    for name in ('IntegerProperty', 'FloatProperty', 'StringProperty',
                 'TextProperty', 'BooleanProperty', 'DateTimeProperty',
                 'JsonProperty', 'KeyProperty', 'ComputedProperty',
                 'UserProperty', 'BlobProperty', 'StructuredProperty',
                 'LocalStructuredProperty'):
        setattr(ndb, name, FakeProperty)
    ext.ndb = ndb
    ext.db = _module('google.appengine.ext.db')

    # -- handlers -----------------------------------------------------------
    handlers = _module('handlers')

    class ServiceRequestHandler(object):
        def __init__(self, *args, **kwargs):
            pass

    handlers.ServiceRequestHandler = ServiceRequestHandler
    handlers.AdminRequestHandler = ServiceRequestHandler
    handlers.APIRequestHandler = ServiceRequestHandler
    handlers.WebRequestHandler = ServiceRequestHandler
    handlers.AuthorizedAPIRequestHandler = ServiceRequestHandler

    stats_pkg = _module('handlers.statistics')
    handlers.statistics = stats_pkg

    game_len = _module('handlers.statistics.game_len_prediction')

    class GameLength(FakeModel):
        pass

    game_len.GameLength = GameLength
    stats_pkg.game_len_prediction = game_len

    # -- objects ------------------------------------------------------------
    objects = _module('objects')

    global_dictionary = _module('objects.global_dictionary')

    class GlobalDictionaryWord(FakeModel):
        # Replaced by the runner.
        @staticmethod
        def get(word):
            return None

    global_dictionary.GlobalDictionaryWord = GlobalDictionaryWord
    global_dictionary.get_langs = lambda: ['ru']
    objects.global_dictionary = global_dictionary

    game_results_log = _module('objects.game_results_log')

    class GameLog(FakeModel):
        pass

    game_results_log.GameLog = GameLog
    objects.game_results_log = game_results_log

    legacy_game_history = _module('objects.legacy_game_history')

    class GameHistory(FakeModel):
        HAT_STANDART = 0
        string_repr = ['guessed', 'failed', 'not_explained']

    legacy_game_history.GameHistory = GameHistory
    objects.legacy_game_history = legacy_game_history

    total_statistics = _module('objects.total_statistics_object')
    total_statistics.ndb = ndb

    class DailyStatistics(FakeModel):
        pass

    class TotalStatistics(FakeModel):
        pass

    class GamesForPlayerCount(FakeModel):
        pass

    total_statistics.DailyStatistics = DailyStatistics
    total_statistics.TotalStatistics = TotalStatistics
    total_statistics.GamesForPlayerCount = GamesForPlayerCount
    objects.total_statistics_object = total_statistics

    unknown_word = _module('objects.unknown_word')

    class UnknownWord(FakeModel):
        pass

    unknown_word.UnknownWord = UnknownWord
    objects.unknown_word = unknown_word

    return ndb
