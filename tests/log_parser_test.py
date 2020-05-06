# coding=utf-8

import unittest2
import json
from handlers.statistics.calculation import AddGameHandler

TEST_LOG_V2 = '{"version":"2.0","time_zone_offset":10800000,"attempts":[{"from":0,"to":1,"word":"цемент",' \
              '"time":13777,"extra_time":0,"outcome":"guessed"},{"from":0,"to":1,"word":"кочегар","time":6230,' \
              '"extra_time":3},{"from":1,"to":2,"word":"отгул","time":6219,"extra_time":0,"outcome":"guessed"},' \
              '{"from":1,"to":2,"word":"стопка","time":4276,"extra_time":0,"outcome":"guessed"},{"from":1,"to":2,' \
              '"word":"бросок","time":5577,"extra_time":0,"outcome":"guessed"},{"from":1,"to":2,"word":"молочко",' \
              '"time":6311,"extra_time":0,"outcome":"guessed"},{"from":1,"to":2,"word":"кислород","time":612,' \
              '"extra_time":2267,"outcome":"guessed"},{"from":2,"to":3,"word":"пуп","time":20008,"extra_time":3},' \
              '{"from":3,"to":0,"word":"смотритель","time":12813,"extra_time":0,"outcome":"guessed"},{"from":3,' \
              '"to":0,"word":"коэффициент","time":6596,"extra_time":0,"outcome":"guessed"},{"from":3,"to":0,' \
              '"word":"новинка","time":3592,"extra_time":3,"outcome":"guessed"},{"from":0,"to":2,"word":"вакса",' \
              '"time":23003,"extra_time":3},{"from":1,"to":3,"word":"водичка","time":8430,"extra_time":0,' \
              '"outcome":"guessed"},{"from":1,"to":3,"word":"оборотень","time":4807,"extra_time":0,' \
              '"outcome":"guessed"},{"from":1,"to":3,"word":"перелом","time":5382,"extra_time":0,' \
              '"outcome":"guessed"},{"from":1,"to":3,"word":"рукав","time":4379,"extra_time":3},{"from":2,"to":0,' \
              '"word":"похолодание","time":8254,"extra_time":0,"outcome":"guessed"},{"from":2,"to":0,"word":"карета",' \
              '"time":6482,"extra_time":0,"outcome":"guessed"},{"from":2,"to":0,"word":"срок","time":3795,' \
              '"extra_time":0,"outcome":"guessed"},{"from":2,"to":0,"word":"жест","time":4201,"extra_time":0,' \
              '"outcome":"guessed"},{"from":2,"to":0,"word":"котлета","time":267,"extra_time":3},{"from":3,"to":1,' \
              '"word":"си","time":12917,"extra_time":0,"outcome":"guessed"},{"from":3,"to":1,"word":"жид",' \
              '"time":8489,"extra_time":0,"outcome":"guessed"},{"from":3,"to":1,"word":"ладья","time":1597,' \
              '"extra_time":3},{"from":0,"to":3,"word":"бутылка","time":9396,"extra_time":0,"outcome":"guessed"},' \
              '{"from":0,"to":3,"word":"электрон","time":4771,"extra_time":0,"outcome":"guessed"},{"from":0,"to":3,' \
              '"word":"дальность","time":2727,"extra_time":0,"outcome":"guessed"},{"from":0,"to":3,"word":"пшеница",' \
              '"time":290,"extra_time":0,"outcome":"guessed"},{"from":0,"to":3,"word":"курс","time":5816,' \
              '"extra_time":1972},{"from":1,"to":0,"word":"патиссон","time":36763,"extra_time":3},{"from":2,"to":1,' \
              '"word":"рожа","time":9799,"extra_time":0,"outcome":"guessed"},{"from":2,"to":1,"word":"зуд",' \
              '"time":5328,"extra_time":0,"outcome":"guessed"},{"from":2,"to":1,"word":"певец","time":3040,' \
              '"extra_time":0,"outcome":"guessed"},{"from":2,"to":1,"word":"курс","time":3051,"extra_time":0,' \
              '"outcome":"guessed"},{"from":2,"to":1,"word":"лгун","time":1779,"extra_time":3},{"from":3,"to":2,' \
              '"word":"водопой","time":9121,"extra_time":0,"outcome":"failed"},{"from":3,"to":2,"word":"синица",' \
              '"time":13886,"extra_time":3},{"from":0,"to":1,"word":"комар","time":7075,"extra_time":0,' \
              '"outcome":"guessed"},{"from":0,"to":1,"word":"лотерея","time":4616,"extra_time":0,' \
              '"outcome":"guessed"},{"from":0,"to":1,"word":"съемка","time":9063,"extra_time":0,"outcome":"guessed"},' \
              '{"from":0,"to":1,"word":"гробница","time":2240,"extra_time":2323},{"from":1,"to":2,"word":"гробница",' \
              '"time":32050,"extra_time":3}],"start_timestamp":1582558022018,"end_timestamp":1582558610857}'
WORDS_ORIG_CORRECT = [u'цемент', u'кочегар', u'отгул', u'стопка', u'бросок', u'молочко', u'кислород', u'пуп',
                      u'смотритель', u'коэффициент', u'новинка', u'вакса', u'водичка', u'оборотень', u'перелом',
                      u'рукав', u'похолодание', u'карета', u'срок', u'жест', u'котлета', u'си', u'жид', u'ладья',
                      u'бутылка', u'электрон', u'дальность', u'пшеница', u'курс', u'патиссон', u'рожа', u'зуд',
                      u'певец', u'лгун', u'водопой', u'синица', u'комар', u'лотерея', u'съемка', u'гробница']
SEEN_WORDS_TIME_CORRECT = {0: 14, 2: 6, 3: 4, 4: 6, 5: 6, 6: 3, 8: 13, 9: 7, 10: 4, 12: 8, 13: 5, 14: 5, 16: 8, 17: 6,
                           18: 4, 19: 4, 21: 13, 22: 8, 24: 9, 25: 5, 26: 3, 28: 3, 30: 10, 31: 5, 32: 3, 36: 7, 37: 5,
                           38: 9}
WORDS_OUTCOME_CORRECT = {0: 'guessed', 2: 'guessed', 3: 'guessed', 4: 'guessed', 5: 'guessed', 6: 'guessed',
                         8: 'guessed', 9: 'guessed', 10: 'guessed', 12: 'guessed', 13: 'guessed', 14: 'guessed',
                         16: 'guessed', 17: 'guessed', 18: 'guessed', 19: 'guessed', 20: 'removed', 21: 'guessed',
                         22: 'guessed', 24: 'guessed', 25: 'guessed', 26: 'guessed', 27: 'removed', 28: 'guessed',
                         30: 'guessed', 31: 'guessed', 32: 'guessed', 34: 'failed', 36: 'guessed', 37: 'guessed',
                         38: 'guessed'}
EXPLAINED_AT_ONCE_CORRECT = {0: True, 2: True, 3: True, 4: True, 5: True, 6: True, 8: True, 9: True, 10: True, 12: True,
                             13: True, 14: True, 16: True, 17: True, 18: True, 19: True, 21: True, 22: True, 24: True,
                             25: True, 26: True, 28: True, 30: True, 31: True, 32: True, 36: True, 37: True, 38: True}
EXPLAINED_PAIR_CORRECT = {0: (0, 1), 2: (1, 2), 3: (1, 2), 4: (1, 2), 5: (1, 2), 6: (1, 2), 8: (3, 0), 9: (3, 0),
                          10: (3, 0), 12: (1, 3), 13: (1, 3), 14: (1, 3), 16: (2, 0), 17: (2, 0), 18: (2, 0),
                          19: (2, 0), 21: (3, 1), 22: (3, 1), 24: (0, 3), 25: (0, 3), 26: (0, 3), 28: (2, 1),
                          30: (2, 1), 31: (2, 1), 32: (2, 1), 36: (0, 1), 37: (0, 1), 38: (0, 1)}
PLAYERS_NUM_CORRECT = 4
START_CORRECT = 1582568822018
STOP_CORRECT = 1582569410857


class LogParserTest(unittest2.TestCase):
    def setUp(self):
        self.parse_log_v2 = AddGameHandler().parse_log_v2

    def testParseLog(self):
        words_orig, seen_words_time, words_outcome, explained_at_once, explained_pair, players_num, start, stop = \
            self.parse_log_v2(json.loads(TEST_LOG_V2))
        self.assertEqual(words_orig, WORDS_ORIG_CORRECT)
        self.assertEqual(dict(seen_words_time), SEEN_WORDS_TIME_CORRECT)
        self.assertEqual(words_outcome, WORDS_OUTCOME_CORRECT)
        self.assertEqual(explained_at_once, EXPLAINED_AT_ONCE_CORRECT)
        self.assertEqual(explained_pair, EXPLAINED_PAIR_CORRECT)
        self.assertEqual(players_num, PLAYERS_NUM_CORRECT)
        self.assertEqual(start, START_CORRECT)
        self.assertEqual(stop, STOP_CORRECT)


if __name__ == '__main__':
    unittest2.main()
