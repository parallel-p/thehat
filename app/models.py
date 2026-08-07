# -*- coding: utf-8 -*-
"""Datastore models, ported from the python27 app to ``google-cloud-ndb``.

Kind names, property names, property types and indexed-ness are byte-for-byte
what the old app wrote, because the python27 version keeps reading and writing
the same entities during the traffic split. Do not "clean up" anything here.
"""

from google.cloud import ndb


# --------------------------------------------------------------------------
# objects/user_devices.py
# --------------------------------------------------------------------------


class User(ndb.Model):
    user_id = ndb.StringProperty()
    # Legacy App Engine Users API value. We never write it; it is declared so
    # that existing entities deserialize cleanly.
    user_object = ndb.UserProperty()
    devices = ndb.KeyProperty(repeated=True)
    values = ndb.JsonProperty(default={})
    version = ndb.IntegerProperty(default=0)
    devices_values = ndb.JsonProperty(default={})
    devices_version = ndb.IntegerProperty(default=0)
    localization = ndb.StringProperty(default='ru_RU')


class Device(ndb.Model):
    device_id = ndb.StringProperty()
    values = ndb.JsonProperty(default={})
    version = ndb.IntegerProperty(default=0)


class OwnedModel(ndb.Model):
    """Base class whose ``query`` fans out over a user's linked devices."""

    owner = ndb.KeyProperty()

    @classmethod
    def query(cls, user, *args, **kwargs):
        if not isinstance(user, ndb.Key):
            raise TypeError()
        if user.kind() == 'User':
            user_entity = user.get()
            devices = list(user_entity.devices) if user_entity else []
            devices.append(user)
            filt = cls.owner.IN(devices)
        elif user.kind() == 'Device':
            filt = cls.owner == user
        else:
            raise ValueError()
        return super(OwnedModel, cls).query(filt, *args, **kwargs)


def get_device(device_id):
    """Return the key of ``device_id``, creating the Device if it is new.

    Creating on read is what the python27 app did; the legacy Java client has
    no registration step and relies on it.
    """
    return (Device.query(Device.device_id == device_id).get(keys_only=True) or
            Device(device_id=device_id).put())


def get_device_and_user(device_id):
    device = get_device(device_id)
    user = User.query(User.devices == device).get(keys_only=True)
    if user is None:
        return device, device
    return device, user


# --------------------------------------------------------------------------
# objects/user_dictionary_word.py
# --------------------------------------------------------------------------


def validate_word(prop, value):
    return value.strip().lower()


class UserDictionaryWord(OwnedModel):
    word = ndb.StringProperty(validator=validate_word)
    status = ndb.StringProperty(default="")
    dictionary = ndb.IntegerProperty(indexed=False, default=0)
    used = ndb.IntegerProperty(indexed=False, default=0)
    added = ndb.IntegerProperty(indexed=False, default=0)
    version = ndb.IntegerProperty(default=0)


# --------------------------------------------------------------------------
# objects/global_dictionary.py
# --------------------------------------------------------------------------


class WordLookup(ndb.Model):
    proper_word = ndb.StringProperty(required=True)


class WordFrequency(ndb.Model):
    """Corpus frequency of a word, in uses per million; the entity id is the
    word itself. Written once by the legacy admin importer and never since —
    read here only for the difficulty-vs-frequency statistic."""
    word = ndb.StringProperty()
    frequency = ndb.FloatProperty()


def _danger(self):
    # Preserved verbatim from the python27 app, where `/` on two ints is floor
    # division. The value is therefore ~always 0. Changing it to true division
    # would rewrite an indexed property that the old version still reads, so
    # the legacy behaviour is kept on purpose.
    return (self.failed_times // self.used_times) if self.used_times != 0 else 0


class GlobalDictionaryWord(ndb.Model):
    cnt = ndb.IntegerProperty()
    timestamp = ndb.DateTimeProperty(auto_now=True)
    word = ndb.StringProperty(indexed=True)
    E = ndb.FloatProperty(default=50.0)
    D = ndb.FloatProperty(default=50.0 / 3)
    used_times = ndb.IntegerProperty(default=0)
    guessed_times = ndb.IntegerProperty(default=0)
    failed_times = ndb.IntegerProperty(default=0)
    total_explanation_time = ndb.IntegerProperty(default=0)
    counts_by_expl_time = ndb.JsonProperty(default=[])
    # StringProperty(indexed=False) in legacy ndb *was* TextProperty with
    # _indexed flipped; google-cloud-ndb splits them, and TextProperty is the
    # wire-compatible spelling.
    used_games = ndb.TextProperty(repeated=True)
    tags = ndb.TextProperty()
    danger = ndb.ComputedProperty(_danger)
    deleted = ndb.BooleanProperty(default=False)
    lang = ndb.StringProperty(default='ru')

    @staticmethod
    def get(word):
        """Look a word up, following the WordLookup alias table."""
        word = word.lower()
        entity = ndb.Key(GlobalDictionaryWord, word).get()
        if entity:
            return entity
        lookup = ndb.Key(WordLookup, word).get()
        if not lookup:
            return None
        return ndb.Key(GlobalDictionaryWord, lookup.proper_word).get()


class Dictionary(ndb.Model):
    gcs_key = ndb.StringProperty()


def get_langs():
    return [key.id() for key in Dictionary.query().fetch(keys_only=True)]


# --------------------------------------------------------------------------
# objects/game_results_log.py
# --------------------------------------------------------------------------


IGNORE_REASON = {
    'old_version': "This game log was created by old version of the application and is not supported",
    'suspect_too_quick_explanation': "Most of the words in this game were explained too quickly.",
    'suspect_too_little_words': "Too little of words used in this game were explained",
    'format-error': "Log of this game isn't formatted properly",
    'not_hat': "This is not an original hat game",
    'aborted': "This game was aborted on device",
    'manual': "This game was marked as ignored by administrator",
}

# The old EnumProperty numbered the reasons by iterating IGNORE_REASON, so the
# codes are whatever order CPython 2.7's hash table produced -- not something the
# source alone tells you. These values were derived by running that iteration
# under python 2.7 and independently confirmed against production: 3000 ignored
# GameLog entities carry codes 0 and 2, and re-classifying each of them with the
# ported parser agrees with this table 100% of the time
# (scripts/recover_reason_enum.py). Games ignored by the py3 version therefore
# keep the same codes as before.
REASON_CODES = {
    'suspect_too_little_words': 0,
    'not_hat': 1,
    'suspect_too_quick_explanation': 2,
    'manual': 3,
    'old_version': 4,
    'aborted': 5,
    'format-error': 6,
}

REASON_BY_CODE = {code: name for name, code in REASON_CODES.items()}


class StatisticVersion(ndb.Model):
    version = ndb.IntegerProperty()


class GameLog(ndb.Model):
    # See the note on GlobalDictionaryWord.tags: unindexed strings are
    # TextProperty in google-cloud-ndb.
    json = ndb.TextProperty()
    time = ndb.DateTimeProperty()
    ignored = ndb.BooleanProperty(default=False)
    # Was EnumProperty(IGNORE_REASON) -- an indexed IntegerProperty on the wire.
    reason = ndb.IntegerProperty()

    def set_reason(self, name):
        self.reason = REASON_CODES[name]


# --------------------------------------------------------------------------
# objects/unknown_word.py
# --------------------------------------------------------------------------


class UnknownWord(ndb.Model):
    times_used = ndb.IntegerProperty(default=0)
    ignored = ndb.BooleanProperty(default=False)
    word = ndb.StringProperty()


# --------------------------------------------------------------------------
# objects/total_statistics_object.py
# --------------------------------------------------------------------------


class DailyStatistics(ndb.Model):
    date = ndb.DateTimeProperty()
    words_used = ndb.IntegerProperty(default=0)
    players_participated = ndb.IntegerProperty(default=0)
    games = ndb.IntegerProperty(default=0)
    total_game_duration = ndb.IntegerProperty(default=0)


class TotalStatistics(ndb.Model):
    games = ndb.IntegerProperty(default=0)
    words_used = ndb.IntegerProperty(default=0)
    by_hour = ndb.JsonProperty(default=[0 for _ in range(24 * 7)])

    @classmethod
    def get(cls):
        # A fresh instance must not share the class-level default list, or
        # `by_hour[h] += 1` would mutate it for every later instance.
        return (ndb.Key(cls, 'total_statistics').get() or
                TotalStatistics(id='total_statistics', by_hour=[0 for _ in range(24 * 7)]))


class GamesForPlayerCount(ndb.Model):
    games = ndb.IntegerProperty(default=0)
    player_count = ndb.IntegerProperty()


class StatsCache(ndb.Model):
    """One computed statistics blob, keyed by the name of what it holds.

    New with the python3 app; the python27 version used memcache, which the
    runtime no longer offers. The in-process cache this backs is per instance
    and min_instances is 0, so nearly every real visit used to land on an
    empty one and pay the full recomputation. Here the answer outlives the
    instance that computed it.

    Compressed because the largest of them -- the whole played dictionary,
    for the random sample -- is ~800 KB of JSON and ~145 KB once zlib has had
    it, against Datastore's 1 MB entity limit. `computed` is what the pages
    read to decide whether the daily refresh is still running.
    """
    payload = ndb.JsonProperty(compressed=True)
    # Set explicitly by whoever computed the payload, not auto_now: the field
    # means "when these numbers were worked out", and auto_now would let any
    # later put() for any reason re-date stale numbers as fresh.
    computed = ndb.DateTimeProperty()


# --------------------------------------------------------------------------
# handlers/statistics/game_len_prediction.py
# --------------------------------------------------------------------------


class GameLength(ndb.Model):
    player_count = ndb.IntegerProperty()
    lens = ndb.JsonProperty()
    type = ndb.StringProperty()


# --------------------------------------------------------------------------
# The daily word duel (/duel). New with the python3 app.
# --------------------------------------------------------------------------


class WordDuel(ndb.Model):
    """One day's puzzle: ten pairs of words, and which of each is harder.

    The entity id is the date the puzzle belongs to, ``YYYY-MM-DD`` in the
    game's timezone (see `app.duel.DUEL_TZ`) -- so a day and its puzzle are
    the same thing and there is no way to have two of one.

    Written once, by whoever asks for a day first (usually the daily cron),
    and never again: the puzzle a reader shares has to be the puzzle everyone
    else got, and it is also the record of which words have been spent.

    `pairs` is [[left, right, harder, E_left, E_right], ...] where `harder` is
    0 or 1 -- the index of the harder word, already in the order the page
    shows them, so that rendering the puzzle is a read and nothing more.

    The two ratings are stored rather than looked up when the page is drawn,
    because they are what the pair was chosen on. A word's difficulty moves
    every time it is played; a puzzle that showed today's numbers as its
    working could end up showing a pair that no longer clears the bar it was
    picked by, or -- given enough drift -- the wrong answer entirely.
    """
    day = ndb.IntegerProperty()
    pairs = ndb.JsonProperty()
    created = ndb.DateTimeProperty()
