from google.appengine.ext import deferred
from google.appengine.ext import ndb

BATCH_SIZE = 100

def deferred_map(model_kind, function, cursor=None, keys_only=False, write=False):
    data, curs, more = ndb.Query(kind=model_kind).fetch_page(BATCH_SIZE, start_cursor=cursor, keys_only=keys_only)
    for entity in data:
        function(entity)
    if write:
        ndb.put_multi(data)
    if len(data) > 0 and more and curs:
        deferred.defer(deferred_map, model_kind, function, curs, keys_only, write)
