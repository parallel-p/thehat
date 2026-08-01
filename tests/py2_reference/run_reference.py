# -*- coding: utf-8 -*-
"""Generate golden statistics traces by running the python27 code, under python 2.7.

    ~/.pyenv/versions/2.7.18/bin/python tests/py2_reference/run_reference.py \\
        --logs tests/fixtures/game_logs.jsonl \\
        --words tests/fixtures/word_ratings.json \\
        --out tests/fixtures/stats_golden.jsonl

Each output line is the full ordered trace of what ``AddGameHandler.post`` would
have written for one game log: every ``update_word`` call with the resulting
TrueSkill mu/sigma, plus the aggregate updates. ``tests/test_stats_golden.py``
asserts the python3 port produces exactly the same trace.

This deliberately executes ``legacy/handlers/statistics/calculation.py`` and the
vendored ``legacy/trueskill`` package as-is.
"""

import argparse
import imp
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LEGACY = os.path.join(ROOT, 'legacy')

sys.path.insert(0, HERE)
# So that `import trueskill` finds the vendored, patched 0.4.1 copy.
sys.path.insert(0, LEGACY)

import shim  # noqa: E402

ndb = shim.install()

# environment.py is used unmodified; it pulls in legacy/trueskill.
environment = imp.load_source('reference_environment',
                              os.path.join(LEGACY, 'environment.py'))
sys.modules['environment'] = environment

calculation = imp.load_source(
    'reference_calculation',
    os.path.join(LEGACY, 'handlers', 'statistics', 'calculation.py'))


class FakeWord(object):
    def __init__(self, word, E, D, lang):
        self.word = word
        self.E = E
        self.D = D
        self.lang = lang


class FakeLog(object):
    def __init__(self, entity_id, payload):
        self.entity_id = entity_id
        self.json = payload
        self.time = None
        self.ignored = False
        self.reason = None

    def put(self):
        return None


class Aborted(Exception):
    pass


def make_handler(words_by_key, langs):
    """A handler whose writes are recorded instead of performed."""

    class ReferenceHandler(calculation.AddGameHandler):
        def __init__(self):
            self.trace = []
            self.request = self

        # -- request stub --
        def get(self, name, default=None):
            return 'fake-urlsafe' if name == 'game_key' else default

        def abort(self, code):
            raise Aborted(code)

        # -- recorded writes --
        @staticmethod
        def check_word(word):
            pass

        def update_daily_statistics(self, game_date, word_count, players_count, duration):
            self.trace.append(['daily', game_date, word_count, players_count, duration])

        def update_statistics_by_player_count(self, player_count):
            self.trace.append(['by_player_count', player_count])

        def update_total_statistics(self, word_count, game_time=None):
            self.trace.append(['total', word_count, game_time])

        def update_game_len_prediction(self, player_count, game_type, game_len):
            self.trace.append(['game_len', player_count, game_type, game_len])

        def update_word(self, word, word_outcome, explanation_time, rating, game_key):
            # `rating` is None for words missing from the global dictionary; the
            # real update_word returns early in that case.
            self.trace.append(['word', word, word_outcome, explanation_time,
                               repr(rating.mu) if rating else None,
                               repr(rating.sigma) if rating else None])

    calculation.GlobalDictionaryWord.get = staticmethod(
        lambda word: words_by_key.get(word.lower()))
    calculation.get_langs = lambda: langs
    return ReferenceHandler


def trace_one(handler_class, log_entry, words_by_key):
    handler = handler_class()
    fake_log = FakeLog(log_entry['id'], log_entry['json'])
    shim.FakeKey.current_entity = fake_log
    try:
        handler.post()
        outcome = 'ok'
    except Aborted:
        outcome = 'aborted'
    except calculation.BadGameError as exc:  # pragma: no cover - post catches it
        outcome = 'bad:{}'.format(exc.reason)
    return {
        'id': log_entry['id'],
        'outcome': outcome,
        'ignored': fake_log.ignored,
        'reason': fake_log.reason,
        'time': fake_log.time.isoformat() if fake_log.time else None,
        'trace': handler.trace,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', required=True)
    parser.add_argument('--words', required=True,
                        help='JSON map word -> {"E":.., "D":.., "lang":..}')
    parser.add_argument('--out', required=True)
    parser.add_argument('--langs', default='ru')
    args = parser.parse_args()

    with open(args.words) as handle:
        raw_words = json.load(handle)
    words_by_key = dict(
        (word.lower(), FakeWord(word, spec['E'], spec['D'], spec.get('lang', 'ru')))
        for word, spec in raw_words.items())

    handler_class = make_handler(words_by_key, args.langs.split(','))

    written = 0
    with open(args.logs) as source, open(args.out, 'w') as sink:
        for line in source:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            result = trace_one(handler_class, entry, words_by_key)
            sink.write(json.dumps(result, sort_keys=True) + '\n')
            written += 1
    sys.stderr.write('wrote {} traces to {}\n'.format(written, args.out))


if __name__ == '__main__':
    main()
