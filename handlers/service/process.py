from google.appengine.ext import deferred
from google.appengine.ext import ndb

BATCH_SIZE = 500

def _map(model_kind, function, cursor=None):
    data, curs, more = ndb.Query(kind=model_kind).fetch_page(BATCH_SIZE, start_cursor=cursor)
    for entity in data:
        function(entity)
    if len(data) > 0 and more and curs:
        deferred.defer(_map, model_kind, function, curs)

def map_entities(model_kind, function):
    deferred.defer(_map, model_kind, function)
