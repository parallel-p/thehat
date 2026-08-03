# -*- coding: utf-8 -*-
"""Statistics pipeline -- contract 7 of MIGRATION_PLAN.md §5.

A faithful port of ``handlers/statistics/calculation.py`` ``AddGameHandler``.
"Faithful" is meant literally: several behaviours below are bugs, and they are
reproduced anyway, because the python27 version keeps writing the same entities
during the traffic split and the two versions must not disagree.

The python2 -> python3 traps that actually change numbers here:

1. ``round()``. Python 2 rounds halves away from zero, Python 3 rounds halves to
   even. Explanation times are ``round(ms / 1000.0)`` and land exactly on .5
   whenever ``ms`` ends in 500, so :func:`py2_round` is used instead.
2. ``/`` on two ints is floor division in python2. Reproduced with ``//``.
3. Dict iteration order. ``seen_words_time`` and ``current_words_time`` are
   keyed by small non-negative word indices. CPython 2.7 iterates such a dict in
   *slot* order, python3 in insertion order, and that order decides how ties are
   broken when rating groups are sorted -- which changes the ratings. Both dicts
   are therefore :class:`app.py2compat.Py2IntDict`, which reproduces the old
   table layout exactly.
"""

import datetime
import json
import logging
from collections import defaultdict

from google.cloud import ndb

from app.py2compat import Py2IntDict, py2_round
from app.models import (DailyStatistics, GameLength, GamesForPlayerCount,
                        GameLog, GlobalDictionaryWord, TotalStatistics,
                        UnknownWord, get_langs)
from app.trueskill_env import TRUESKILL_ENVIRONMENT

logger = logging.getLogger(__name__)


class BadGameError(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


MAX_TIME = 5 * 60 * 1000  # 5 minutes
MIN_TIME = 500  # 0.5 second
DEFAULT_OFFSET = 4 * 60 * 60 * 1000


def get_date(time):
    return time - time % (60 * 60 * 24)


# --------------------------------------------------------------------------
# Log parsing
# --------------------------------------------------------------------------


def parse_log(log_db):
    log = json.loads(log_db.json)
    return parse_log_v2(log) if log.get('version') == '2.0' else parse_log_v1(log)


def parse_log_v2(log):
    events = log['attempts']
    words_orig = []
    explained_at_once = dict()
    seen_by_player = defaultdict(lambda: set())
    seen_words_time = Py2IntDict(lambda: 0)
    words_outcome = dict()
    explained_pair = dict()
    players = set()
    start = log.get('start_timestamp')
    end = log.get('end_timestamp')
    offset = log.get('time_zone_offset', DEFAULT_OFFSET)

    if start:
        start += offset
    if end:
        end += offset
    for event in events:
        if event['word'] in words_orig:
            word_num = words_orig.index(event['word'])
        else:
            word_num = len(words_orig)
            words_orig.append(event['word'])
        players.add(event['from'])
        players.add(event['to'])
        seen_by_player[event['from']].add(word_num)
        if event['time'] + event['extra_time'] > MAX_TIME or event['time'] + event['extra_time'] < MIN_TIME:
            words_outcome[word_num] = 'removed'
            continue
        if event.get('outcome') == 'guessed':
            if word_num in seen_by_player[event['to']]:
                seen_words_time.pop(word_num, None)
                continue
            # Legacy quirk: an int is compared against a view of sets, so this
            # is always True. Kept as-is on purpose.
            explained_at_once[word_num] = word_num not in seen_by_player.values()
            explained_pair[word_num] = (event['from'], event['to'])
            words_outcome[word_num] = 'guessed'
            seen_words_time[word_num] += py2_round(
                (event['time'] + event['extra_time']) / 1000.0)
        elif event.get('outcome') == 'failed':
            words_outcome[word_num] = 'failed'
    return (words_orig, seen_words_time, words_outcome, explained_at_once,
            explained_pair, len(players), start, end)


def parse_log_v1(log):
    if log['setup']['type'] == "freeplay":
        raise BadGameError('old_version')
    events = log['events']
    words_orig = [el['word'] for el in log['setup']['words']]
    explained_at_once = [False] * len(words_orig)
    seen_by_player = defaultdict(lambda: set())
    seen_words_time = Py2IntDict(lambda: 0)
    words_outcome = {}
    explained_pair = {}
    current_words_time = Py2IntDict()
    start_timestamp = None
    finish_timestamp = None

    for i in events:
        if i["type"] == "end_game":
            finish_timestamp = i["time"]
    i = 0
    while i < len(events) and events[i]['type'] != 'round_start':
        if events[i]['type'] != 'start_game':
            logger.warning("Unexpected %s event before the first round start",
                           events[i]['type'])
        else:
            start_timestamp = events[i]["time"]
        i += 1
    while i < len(events):
        current_pair = (events[i]['from'], events[i]['to'])
        i += 1
        while i < len(events) and events[i]['type'] != 'round_start':
            event = events[i]
            if event['type'] == 'stripe_outcome':
                words_outcome[event['word']] = event['outcome']
                current_words_time[event['word']] = event['time'] + event['timeExtra']
            elif event['type'] == 'outcome_override':
                if event['word'] not in words_outcome:
                    raise BadGameError("format-error")
                words_outcome[event['word']] = event['outcome']
            else:
                if event['type'] not in ('finish_round', 'end_game', 'pick_stripe'):
                    logger.warning("Event of unknown type %s", event['type'])
            i += 1
        for word in current_words_time.keys():
            if word in seen_by_player[current_pair[0]]:
                seen_words_time.pop(word, None)
                continue
            if current_words_time[word] > MAX_TIME or current_words_time[word] < MIN_TIME:
                words_outcome[word] = 'removed'
            elif words_outcome[word] in ('guessed', 'failed'):
                if word not in seen_words_time:
                    explained_at_once[word] = True
                explained_pair[word] = current_pair
            seen_words_time[word] += py2_round(current_words_time[word] / 1000.0)
            seen_by_player[current_pair[0]].add(word)
        current_words_time.clear()
    player_count = len(log["setup"]["players"]) if "players" in log["setup"] else 0
    try:
        offset = int(log['setup']['meta']['time.offset'])
    except KeyError:
        offset = DEFAULT_OFFSET
    if start_timestamp:
        start_timestamp += offset
    if finish_timestamp:
        finish_timestamp += offset
    return (words_orig, seen_words_time, words_outcome, explained_at_once,
            explained_pair, player_count, start_timestamp, finish_timestamp)


# --------------------------------------------------------------------------
# Datastore updates
# --------------------------------------------------------------------------


def check_word(word):
    if GlobalDictionaryWord.get(word) is None:
        on_server = ndb.Key(UnknownWord, word).get()
        if on_server is None:
            UnknownWord(word=word, id=word, times_used=1).put()
        elif not on_server.ignored:
            on_server.times_used += 1
            on_server.put()


@ndb.transactional()
def update_daily_statistics(game_date, word_count, players_count, duration):
    statistics = (ndb.Key(DailyStatistics, str(game_date)).get() or
                  DailyStatistics(date=datetime.datetime.fromtimestamp(game_date),
                                  id=str(game_date)))
    statistics.words_used += word_count
    statistics.players_participated += players_count
    statistics.games += 1
    statistics.total_game_duration += duration
    statistics.put()


@ndb.transactional()
def update_statistics_by_player_count(player_count):
    statistics = (ndb.Key(GamesForPlayerCount, str(player_count)).get() or
                  GamesForPlayerCount(player_count=player_count,
                                      id=str(player_count)))
    statistics.games += 1
    statistics.put()


@ndb.transactional()
def update_total_statistics(word_count, game_time=None):
    statistics = TotalStatistics.get()
    statistics.games += 1
    statistics.words_used += word_count
    if game_time:
        hour = game_time // (60 * 60) % (24 * 7)
        statistics.by_hour[hour] += 1
    statistics.put()


@ndb.transactional()
def update_word(word, word_outcome, explanation_time, rating, game_key):
    word_db = GlobalDictionaryWord.get(word)
    if not word_db:
        return
    word_db.used_times += 1
    if word_outcome == 'guessed':
        word_db.guessed_times += 1
    elif word_outcome == 'failed':
        word_db.failed_times += 1
    time_sec = explanation_time
    word_db.total_explanation_time += time_sec
    if word_outcome == 'guessed':
        pos = time_sec // 5
        counts = word_db.counts_by_expl_time
        while pos >= len(counts):
            counts.append(0)
        counts[pos] += 1
    word_db.used_games.append(game_key.urlsafe().decode("ascii"))
    word_db.E = rating.mu
    word_db.D = rating.sigma
    word_db.put()


def update_game_len_prediction(player_count, game_type, game_len):
    key = "{0}_{1}".format(game_type, player_count)
    prediction_db = ndb.Key(GameLength, key).get()
    if prediction_db is None:
        GameLength(lens=[game_len], player_count=player_count, type=game_type,
                   id=key).put()
    else:
        prediction_db.lens.append(game_len)
        prediction_db.put()


# --------------------------------------------------------------------------
# The pipeline itself
# --------------------------------------------------------------------------


class GameRater:
    """Holds the per-game rating state that ``AddGameHandler`` kept on self."""

    def __init__(self, word_db, ratings, langs):
        self.word_db = word_db
        self.ratings = ratings
        self.langs = langs

    def rate(self, words, coef=None):
        for lang in self.langs:
            ratings = [{word: self.ratings[word]} for word in words if
                       self.ratings[word] and self.word_db[word].lang == lang]
            if len(ratings) > 1:
                rated = TRUESKILL_ENVIRONMENT.rate(ratings, partial_update=coef)
                for d in rated:
                    word, rate = next(iter(d.items()))
                    self.ratings[word] = rate


def add_game_to_statistic(game_key):
    """Process one game log. Returns a short string for logging/tests."""
    logger.info("Handling log of game %s", game_key.id())
    if game_key.kind() != 'GameLog':
        # GameHistory (the 2014 kind) is not ported; nothing enqueues it.
        return "skipped:kind"
    log_db = game_key.get()
    if log_db is None:
        logger.error("Can't find game log %s", game_key)
        return "skipped:missing"

    try:
        (words_orig, seen_words_time, words_outcome, explained_at_once,
         explained_pair, players_count, start_timestamp,
         finish_timestamp) = parse_log(log_db)

        if start_timestamp and finish_timestamp:
            update_game_len_prediction(players_count, 'game',
                                       finish_timestamp - start_timestamp)
        bad_words_count = 0

        if 2 * len(seen_words_time) < len(words_orig):
            raise BadGameError('suspect_too_little_words')
        for k, v in seen_words_time.items():
            if v < 2:
                bad_words_count += 1
        if 2 * bad_words_count > len(seen_words_time):
            raise BadGameError('suspect_too_quick_explanation')

        for word in words_orig:
            check_word(word)

        word_db = [GlobalDictionaryWord.get(word) for word in words_orig]
        ratings = [TRUESKILL_ENVIRONMENT.create_rating(word.E, word.D) if word
                   else None for word in word_db]
        rater = GameRater(word_db, ratings, get_langs())

        # Four rating passes, in the original order and with the original
        # damping coefficients. Iteration order comes from Py2IntDict.
        d = defaultdict(list)
        for word in seen_words_time:
            if explained_at_once[word] and words_outcome[word] == 'guessed':
                d[explained_pair[word]].append(word)
        for group in d.values():
            group.sort(key=lambda item: -seen_words_time[item])
            rater.rate(group)

        d = defaultdict(list)
        for word in seen_words_time:
            if words_outcome[word] == 'guessed':
                d[explained_pair[word][0]].append(word)
        for group in d.values():
            group.sort(key=lambda item: -seen_words_time[item])
            rater.rate(group, coef=0.3)

        d = defaultdict(list)
        for word in seen_words_time:
            if words_outcome[word] == 'guessed':
                d[explained_pair[word][1]].append(word)
        for group in d.values():
            group.sort(key=lambda item: -seen_words_time[item])
            rater.rate(group, coef=0.8)

        words = [word for word in seen_words_time
                 if words_outcome[word] == 'guessed']
        words.sort(key=lambda item: -seen_words_time[item])
        rater.rate(words, coef=0.6)

        for i in range(len(words_orig)):
            if i in seen_words_time:
                update_word(words_orig[i], words_outcome[i], seen_words_time[i],
                            rater.ratings[i], game_key)

        if start_timestamp:
            start_timestamp //= 1000
            log_db.time = datetime.datetime.fromtimestamp(start_timestamp)
            log_db.put()
            if finish_timestamp:
                finish_timestamp //= 1000
                duration = finish_timestamp - start_timestamp
            else:
                duration = 0
            game_date = get_date(start_timestamp)
            update_daily_statistics(game_date, len(seen_words_time),
                                    players_count, duration)
        update_total_statistics(len(seen_words_time), start_timestamp)
        if players_count:
            update_statistics_by_player_count(players_count)
        return "ok"
    except BadGameError as e:
        log_db.ignored = True
        log_db.set_reason(e.reason)
        log_db.put()
        logger.warning("Did not handle and marked this game as ignored: %s",
                       e.reason)
        return "ignored:{}".format(e.reason)
