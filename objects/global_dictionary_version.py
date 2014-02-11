import constants

__author__ = 'ivan'
from google.appengine.ext import db


class GlobalDictionaryVersion(db.Model):
    version = db.IntegerProperty()

    @staticmethod
    def get_server_version():
        version = GlobalDictionaryVersion.get_by_key_name(constants.version_key)
        return 0 if version is None else int(version.version)

    @staticmethod
    def update_version():
        version = GlobalDictionaryVersion.get_by_key_name(constants.version_key)
        if version is None:
            version = GlobalDictionaryVersion(key_name=constants.version_key, version=1)
        else:
            version.version += 1
        version.put()