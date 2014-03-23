__author__ = 'nikolay'

import json
import unittest, os, urllib2

import webapp2
from google.appengine.ext import testbed, ndb

from objects.global_dictionary_word import GlobalDictionaryWord
from objects.game_results_log import GameLog
from handlers.legacy_game_history_handler import GameHistory, WordGuessResult, Word, Round
import main

LOG_JSON = '''
{"events":[{"type":"start_game","time":1394351741458},
{"type":"round_start","to":1,"from":0},
{"type":"pick_stripe","word":21},
{"word":21,"timeExtra":1093,"time":10000,"type":"stripe_outcome","outcome":"guessed"},
{"type":"finish_round"},
{"type":"round_start","to":0,"from":1},
{"type":"pick_stripe","word":38},
{"word":38,"timeExtra":0,"time":5062,"type":"stripe_outcome","outcome":"guessed"},
{"type":"pick_stripe","word":17},
{"word":17,"timeExtra":1471,"time":4938,"type":"stripe_outcome","outcome":"timed-out"},
{"type":"finish_round"},
{"type":"round_start","to":1,"from":0},
{"type":"pick_stripe","word":23},
{"word":23,"timeExtra":1519,"time":10000,"type":"stripe_outcome","outcome":"timed-out"},
{"type":"finish_round"},
{"type":"round_start","to":0,"from":1},
{"type":"pick_stripe","word":42},
{"word":42,"timeExtra":0,"time":5528,"type":"stripe_outcome","outcome":"guessed"},
{"type":"pick_stripe","word":31},
{"word":31,"timeExtra":0,"time":4171,"type":"stripe_outcome","outcome":"guessed"},
{"type":"pick_stripe","word":35},
{"word":35,"timeExtra":1189,"time":301,"type":"stripe_outcome","outcome":"timed-out"},
{"type":"finish_round"},
{"type":"round_start","to":1,"from":0},
{"type":"pick_stripe","word":2},
{"word":2,"timeExtra":3021,"time":10000,"type":"stripe_outcome","outcome":"timed-out"},
{"type":"finish_round"},
{"type":"round_start","to":0,"from":1},
{"type":"pick_stripe","word":22},
{"word":2,"timeExtra":0,"time":7902,"type":"stripe_outcome","outcome":"guessed"},
{"type":"pick_stripe","word":41},
{"word":41,"timeExtra":1897,"time":2098,"type":"stripe_outcome","outcome":"failed"},
{"type":"finish_round"},
{"type":"end_game","aborted":false,"time":1394352550926}],
"setup":{"type":"quick","words":[
{"origin":"random","word":"a"},
{"origin":"random","word":"b"},
{"origin":"random","word":"c"},
{"origin":"random","word":"d"},
{"origin":"random","word":"e"},
{"origin":"random","word":"f"},
{"origin":"random","word":"g"},
{"origin":"random","word":"h"},
{"origin":"random","word":"i"},
{"origin":"random","word":"j"},
{"origin":"random","word":"k"},
{"origin":"random","word":"l"},
{"origin":"random","word":"m"},
{"origin":"random","word":"n"},
{"origin":"random","word":"o"},
{"origin":"random","word":"p"},
{"origin":"random","word":"q"},
{"origin":"random","word":"r"},
{"origin":"random","word":"s"},
{"origin":"random","word":"t"},
{"origin":"random","word":"u"},
{"origin":"random","word":"v"},
{"origin":"random","word":"w"},
{"origin":"random","word":"x"},
{"origin":"random","word":"y"},
{"origin":"random","word":"z"},
{"origin":"random","word":"aa"},
{"origin":"random","word":"ab"},
{"origin":"random","word":"ac"},
{"origin":"random","word":"ad"},
{"origin":"random","word":"ae"},
{"origin":"random","word":"af"},
{"origin":"random","word":"ag"},
{"origin":"random","word":"ah"},
{"origin":"random","word":"ai"},
{"origin":"random","word":"aj"},
{"origin":"random","word":"ak"},
{"origin":"random","word":"al"},
{"origin":"random","word":"am"},
{"origin":"random","word":"an"},
{"origin":"random","word":"ao"},
{"origin":"random","word":"ap"},
{"origin":"random","word":"aq"},
{"origin":"random","word":"ar"},
{"origin":"random","word":"as"},
{"origin":"random","word":"at"},
{"origin":"random","word":"au"},
{"origin":"random","word":"av"},
{"origin":"random","word":"aw"},
{"origin":"random","word":"ax"},
{"origin":"random","word":"ay"},
{"origin":"random","word":"az"}],
"meta":{"game.quick.players":"2","game.id.local":"3e4574b5-078e-45e1-8f23-3badd72ba914","game.limit.round":"0",
"game.words.per.player":"30","game.time.extra":"3","game.id":"3e4574b5-078e-45e1-8f23-3badd72ba914",
"game.pairs.each-to-each":"false","game.words.extra":"random","game.time.main":"10"},
"players":[{"random":false,"type":"OWNER_RANDOM","id":"owner-07401315-ff99-453b-9b2a-a6fdf314bb11","name":"aaa"},
{"random":true,"type":"RANDOM","id":"rnd-0a897476-3816-47e5-a64a-dd92d0d5bfc0","name":"bbb"}]}}
'''

EXPECTED_TIME = {21: 11, 38: 5, 17: 6, 23: 12, 42: 6, 31: 4, 35: 1, 2: 21, 41: 4}
EXPECTED_OUTCOME = {21: 'guessed', 38: 'guessed', 17: 'timed-out', 23: 'timed-out',
                    42: 'guessed', 31: 'guessed', 35: 'timed-out', 2: 'guessed', 41: 'failed'}
PARSED_LOG = json.loads(LOG_JSON)
WORDS = [el['word'] for el in PARSED_LOG['setup']['words']]
EXPECTED_RATES = [
    [41, 42, 38, 31],  #of pair (0,1)
    [2, 21, 42, 38, 31]  #overall
]
HISTORY = GameHistory(
    guess_results=[WordGuessResult(result=a, round_=b, time_sec=c, word=d) for a, b, c, d in zip(
        [3L, 3L, 3L, 1L, 0L, 0L, 0L, 0L, 0L, 0L, 0L, 3L],
        [0L, 1L, 2L, 3L, 4L, 4L, 5L, 5L, 5L, 6L, 6L, 6L],
        [20.000975847244263, 20.01230001449585, 20.02179503440857, 14.53020191192627, 9.769454002380371,
         20.000168800354004, 4.209316968917847, 12.527299165725708, 19.002864122390747, 7.204860925674438,
         17.94984197616577, 20.022836923599243],
        [3L, 22L, 24L, 4L, 3L, 10L, 34L, 24L, 23L, 30L, 2L, 20L]
    )],
    rounds=[Round(player_explain=a, player_guess=b) for a, b in zip(
        [0L, 1L, 0L, 1L, 0L, 1L, 0L],
        [1L, 0L, 1L, 0L, 1L, 0L, 1L]
    )],
    words=[Word(text="word{}".format(i)) for i in range(35)]
)
H_EXPECTED_TIME = {3: 30, 22: 20, 24: 28, 4: 15, 10: 10, 34: 4, 23: 6, 30: 7, 2: 11, 20: 2}
H_EXPECTED_OUTCOME = {3: 'guessed', 22: 'timed-out', 24: 'guessed', 4: 'failed', 10: 'guessed', 34: 'guessed',
                      23: 'guessed', 30: 'guessed', 2: 'guessed', 20: 'timed-out'}
H_EXPECTED_RATES = [
    [2, 10, 30],  #of pair (0,1)
    [4, 23, 34],  #of pair (1, 0)
    [3, 24, 2, 10, 30, 23, 34]  #overall
]

def put_word(word):
    return GlobalDictionaryWord(id=word, word=word).put()


def get_word(word):
    return ndb.Key(GlobalDictionaryWord, word).get()


class RecalcRatingTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub(root_path=os.path.join(*os.path.split(os.path.curdir)[:-1]))
        self.taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
        self.testbed.setup_env(
            USER_EMAIL='test@example.com',
            USER_ID='123',
            USER_IS_ADMIN='1',
            overwrite=True)

    def test_rating_recalculation(self):
        game_words = []
        for i in range(5):
            game_words.append(str(i))
            put_word(str(i))

        request = webapp2.Request.blank('/internal/recalc_rating_after_game')
        request.method = 'POST'
        request.body = "json=%s" % json.dumps(game_words)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        last_rating = 100
        for i in range(5):
            word_db = get_word(str(i))
            self.assertIsNotNone(word_db)
            self.assertGreater(last_rating, word_db.E)
            last_rating = word_db.E

    def test_add_game_log(self):
        GameLog(json=LOG_JSON, id="test_log").put()
        words = [put_word(el).get() for el in WORDS]
        request = webapp2.Request.blank('/internal/add_game_to_statistic')
        request.method = 'POST'
        request.body = "game_id=test_log"
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        for i in range(len(words)):
            if i in EXPECTED_TIME:
                self.assertEqual(words[i].total_explanation_time, EXPECTED_TIME[i])
                if EXPECTED_OUTCOME[i] == 'guessed':
                    self.assertGreaterEqual(len(words[i].counts_by_expl_time), EXPECTED_TIME[i] // 5)
                    self.assertEqual(words[i].counts_by_expl_time[EXPECTED_TIME[i] // 5], 1)
                self.assertEqual(words[i].guessed_times, 1 if EXPECTED_OUTCOME[i] == 'guessed' else 0)
                self.assertEqual(words[i].failed_times, 1 if EXPECTED_OUTCOME[i] == 'failed' else 0)
                self.assertEqual(words[i].used_times, 1)
            else:
                self.assertEqual(words[i].total_explanation_time, 0)
                self.assertEqual(words[i].used_times, 0)
        tasks = self.taskq.get_filtered_tasks(url='/internal/recalc_rating_after_game')
        self.assertEqual(2, len(tasks))
        for el in tasks:
            j = urllib2.unquote(el.payload.split('=')[1]).replace('+', ' ')
            words = json.loads(j)
            self.assertIn([WORDS.index(w) for w in words], EXPECTED_RATES)

    def test_add_game_history(self):
        id = HISTORY.put().id()
        words = [put_word("word{}".format(i)).get() for i in range(35)]
        request = webapp2.Request.blank('/internal/add_legacy_game')
        request.method = 'POST'
        request.body = "game_id={}".format(id)
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)
        for i in range(len(words)):
            if i in H_EXPECTED_TIME:
                self.assertEqual(words[i].total_explanation_time, H_EXPECTED_TIME[i])
                if H_EXPECTED_OUTCOME[i] == 'guessed':
                    self.assertGreaterEqual(len(words[i].counts_by_expl_time), H_EXPECTED_TIME[i] // 5)
                    self.assertEqual(words[i].counts_by_expl_time[H_EXPECTED_TIME[i] // 5], 1)
                self.assertEqual(words[i].guessed_times, 1 if H_EXPECTED_OUTCOME[i] == 'guessed' else 0)
                self.assertEqual(words[i].failed_times, 1 if H_EXPECTED_OUTCOME[i] == 'failed' else 0)
                self.assertEqual(words[i].used_times, 1)
            else:
                self.assertEqual(words[i].total_explanation_time, 0)
                self.assertEqual(words[i].used_times, 0)
        tasks = self.taskq.get_filtered_tasks(url='/internal/recalc_rating_after_game')
        self.assertEqual(3, len(tasks))
        for el in tasks:
            j = urllib2.unquote(el.payload.split('=')[1]).replace('+', ' ')
            words = json.loads(j)
            self.assertIn([int(w[4:]) for w in words], H_EXPECTED_RATES)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest.main()

