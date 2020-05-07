# coding=utf-8

import json

import unittest2
from google.appengine.ext import testbed
from webapp2 import Request

import main
from handlers.statistics.calculation import AddGameHandler
from objects.game_results_log import GameLog

TEST_LOG_V1 = '{"setup":{"players":[{"name":"Вася Пупкин","id":"owner-b9d944fb-2d07-4983-9d87-f670090c4461",' \
              '"type":"OWNER_RANDOM","random":false},{"name":"Маша Кюри","id":"4a1a1954-68ac-4f43-b6b4-ebf69d660861",' \
              '"type":"RANDOM","random":true},{"name":"Петя Чайковский","id":"7447783d-b12d-4136-9c64-400272a14551",' \
              '"type":"RANDOM","random":true}],"meta":{"game.id":"feebebba-d931-4eea-8d6b-7d6e55710c5c",' \
              '"time.offset":"10800000","game.words.extra":"random",' \
              '"game.id.local":"195a8a3a-1e4b-4443-b3b0-cfa4e63287ea","app.platform":"android","app.version":"13",' \
              '"time.zone":"GMT+03:00","game.pairs.each-to-each":"false","game.time.main":"30","game.time.extra":"3",' \
              '"game.words.per.player":"15","game.limit.round":"0"},"words":[{"word":"жокей","origin":"random"},' \
              '{"word":"перфорация","origin":"random"},{"word":"акр","origin":"random"},{"word":"проектировщик",' \
              '"origin":"random"},{"word":"флюктуация","origin":"random"},{"word":"кистень","origin":"random"},' \
              '{"word":"идеализация","origin":"random"},{"word":"обмывание","origin":"random"},{"word":"привыкание",' \
              '"origin":"random"},{"word":"скиф","origin":"random"},{"word":"окулист","origin":"random"},' \
              '{"word":"преступница","origin":"random"},{"word":"дагестанец","origin":"random"},' \
              '{"word":"судопроизводство","origin":"random"},{"word":"скок","origin":"random"},{"word":"деревенщина",' \
              '"origin":"random"},{"word":"номинал","origin":"random"},{"word":"дренаж","origin":"random"},' \
              '{"word":"пилорама","origin":"random"},{"word":"скалка","origin":"random"},{"word":"ликбез",' \
              '"origin":"random"},{"word":"сплетница","origin":"random"},{"word":"перикард","origin":"random"},' \
              '{"word":"одаренность","origin":"random"},{"word":"хотение","origin":"random"},{"word":"черносотенец",' \
              '"origin":"random"},{"word":"пароксизм","origin":"random"},{"word":"голубятня","origin":"random"},' \
              '{"word":"импровизатор","origin":"random"},{"word":"слепок","origin":"random"},{"word":"уникум",' \
              '"origin":"random"},{"word":"беглянка","origin":"random"},{"word":"гордец","origin":"random"},' \
              '{"word":"регистратура","origin":"random"},{"word":"огневик","origin":"random"},{"word":"уклонист",' \
              '"origin":"random"},{"word":"чернушка","origin":"random"},{"word":"распыление","origin":"random"},' \
              '{"word":"метафизика","origin":"random"},{"word":"летосчисление","origin":"random"},{"word":"выборка",' \
              '"origin":"random"},{"word":"осмотрительность","origin":"random"},{"word":"сальник","origin":"random"},' \
              '{"word":"хакер","origin":"random"},{"word":"самоцвет","origin":"random"}],"type":"quick"},"events":[{' \
              '"time":1588671012202,"type":"start_game"},{"from":0,"to":1,"type":"round_start"},{"word":6,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":17310,"timeExtra":0,"word":6,' \
              '"type":"stripe_outcome"},{"word":26,"type":"pick_stripe"},{"outcome":"timed-out","time":12690,' \
              '"timeExtra":2832,"word":26,"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":2,' \
              '"type":"round_start"},{"word":4,"type":"pick_stripe"},{"outcome":"timed-out","time":30000,' \
              '"timeExtra":1324,"word":4,"type":"stripe_outcome"},{"type":"finish_round"},{"from":2,"to":0,' \
              '"type":"round_start"},{"word":42,"type":"pick_stripe"},{"outcome":"guessed","time":14842,' \
              '"timeExtra":0,"word":42,"type":"stripe_outcome"},{"word":9,"type":"pick_stripe"},{"outcome":"guessed",' \
              '"time":13611,"timeExtra":0,"word":9,"type":"stripe_outcome"},{"word":20,"type":"pick_stripe"},' \
              '{"outcome":"timed-out","time":1547,"timeExtra":3022,"word":20,"type":"stripe_outcome"},' \
              '{"type":"finish_round"},{"from":0,"to":2,"type":"round_start"},{"word":20,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":13097,"timeExtra":0,"word":20,"type":"stripe_outcome"},{"word":30,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":15626,"timeExtra":0,"word":30,' \
              '"type":"stripe_outcome"},{"word":17,"type":"pick_stripe"},{"outcome":"timed-out","time":1277,' \
              '"timeExtra":1099,"word":17,"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":0,' \
              '"type":"round_start"},{"word":33,"type":"pick_stripe"},{"outcome":"guessed","time":24084,' \
              '"timeExtra":0,"word":33,"type":"stripe_outcome"},{"word":39,"type":"pick_stripe"},' \
              '{"outcome":"timed-out","time":5916,"timeExtra":449,"word":39,"type":"stripe_outcome"},' \
              '{"type":"finish_round"},{"from":2,"to":1,"type":"round_start"},{"word":36,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":15293,"timeExtra":0,"word":36,"type":"stripe_outcome"},{"word":4,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":14707,"timeExtra":3021,"word":4,' \
              '"type":"stripe_outcome"},{"type":"finish_round"},{"from":0,"to":1,"type":"round_start"},{"word":44,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":7969,"timeExtra":0,"word":44,' \
              '"type":"stripe_outcome"},{"word":3,"type":"pick_stripe"},{"outcome":"guessed","time":16799,' \
              '"timeExtra":0,"word":3,"type":"stripe_outcome"},{"word":35,"type":"pick_stripe"},' \
              '{"outcome":"timed-out","time":5232,"timeExtra":1333,"word":35,"type":"stripe_outcome"},' \
              '{"type":"finish_round"},{"from":1,"to":2,"type":"round_start"},{"word":13,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":18043,"timeExtra":0,"word":13,"type":"stripe_outcome"},{"word":11,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":11411,"timeExtra":0,"word":11,' \
              '"type":"stripe_outcome"},{"word":24,"type":"pick_stripe"},{"outcome":"timed-out","time":546,' \
              '"timeExtra":1692,"word":24,"type":"stripe_outcome"},{"type":"finish_round"},{"from":2,"to":0,' \
              '"type":"round_start"},{"word":15,"type":"pick_stripe"},{"outcome":"guessed","time":8367,"timeExtra":0,' \
              '"word":15,"type":"stripe_outcome"},{"word":37,"type":"pick_stripe"},{"outcome":"guessed","time":12752,' \
              '"timeExtra":0,"word":37,"type":"stripe_outcome"},{"word":31,"type":"pick_stripe"},' \
              '{"outcome":"timed-out","time":8881,"timeExtra":2158,"word":31,"type":"stripe_outcome"},' \
              '{"type":"finish_round"},{"from":0,"to":2,"type":"round_start"},{"word":38,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":13444,"timeExtra":0,"word":38,"type":"stripe_outcome"},{"word":7,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":16556,"timeExtra":3018,"word":7,' \
              '"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":0,"type":"round_start"},{"word":28,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":10785,"timeExtra":0,"word":28,' \
              '"type":"stripe_outcome"},{"word":14,"type":"pick_stripe"},{"outcome":"guessed","time":3512,' \
              '"timeExtra":0,"word":14,"type":"stripe_outcome"},{"word":5,"type":"pick_stripe"},{"outcome":"guessed",' \
              '"time":15703,"timeExtra":1529,"word":5,"type":"stripe_outcome"},{"type":"finish_round"},{"from":2,' \
              '"to":1,"type":"round_start"},{"word":1,"type":"pick_stripe"},{"outcome":"guessed","time":14751,' \
              '"timeExtra":0,"word":1,"type":"stripe_outcome"},{"word":21,"type":"pick_stripe"},{"outcome":"guessed",' \
              '"time":6562,"timeExtra":0,"word":21,"type":"stripe_outcome"},{"word":39,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":6372,"timeExtra":0,"word":39,"type":"stripe_outcome"},{"word":0,' \
              '"type":"pick_stripe"},{"outcome":"timed-out","time":2315,"timeExtra":3007,"word":0,' \
              '"type":"stripe_outcome"},{"type":"finish_round"},{"from":0,"to":1,"type":"round_start"},{"word":34,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":30000,"timeExtra":251,"word":34,' \
              '"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":2,"type":"round_start"},{"word":43,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":5404,"timeExtra":0,"word":43,' \
              '"type":"stripe_outcome"},{"word":8,"type":"pick_stripe"},{"outcome":"guessed","time":5054,' \
              '"timeExtra":0,"word":8,"type":"stripe_outcome"},{"word":2,"type":"pick_stripe"},{"outcome":"guessed",' \
              '"time":10275,"timeExtra":0,"word":2,"type":"stripe_outcome"},{"word":40,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":5483,"timeExtra":0,"word":40,"type":"stripe_outcome"},{"word":19,' \
              '"type":"pick_stripe"},{"outcome":"timed-out","time":3784,"timeExtra":3002,"word":19,' \
              '"type":"stripe_outcome"},{"type":"finish_round"},{"from":2,"to":0,"type":"round_start"},{"word":16,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":7333,"timeExtra":0,"word":16,' \
              '"type":"stripe_outcome"},{"word":35,"type":"pick_stripe"},{"outcome":"guessed","time":20232,' \
              '"timeExtra":0,"word":35,"type":"stripe_outcome"},{"word":23,"type":"pick_stripe"},' \
              '{"outcome":"timed-out","time":2435,"timeExtra":1651,"word":23,"type":"stripe_outcome"},' \
              '{"type":"finish_round"},{"from":0,"to":2,"type":"round_start"},{"word":32,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":9048,"timeExtra":0,"word":32,"type":"stripe_outcome"},{"word":24,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":4461,"timeExtra":0,"word":24,' \
              '"type":"stripe_outcome"},{"word":26,"type":"pick_stripe"},{"outcome":"timed-out","time":16491,' \
              '"timeExtra":3015,"word":26,"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":0,' \
              '"type":"round_start"},{"word":22,"type":"pick_stripe"},{"outcome":"guessed","time":20462,' \
              '"timeExtra":0,"word":22,"type":"stripe_outcome"},{"word":29,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":9217,"timeExtra":0,"word":29,"type":"stripe_outcome"},{"word":23,' \
              '"type":"pick_stripe"},{"outcome":"timed-out","time":321,"timeExtra":1624,"word":23,' \
              '"type":"stripe_outcome"},{"type":"finish_round"},{"from":2,"to":1,"type":"round_start"},{"word":17,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":28350,"timeExtra":0,"word":17,' \
              '"type":"stripe_outcome"},{"word":23,"type":"pick_stripe"},{"outcome":"timed-out","time":1650,' \
              '"timeExtra":2120,"word":23,"type":"stripe_outcome"},{"type":"finish_round"},{"from":0,"to":1,' \
              '"type":"round_start"},{"word":12,"type":"pick_stripe"},{"outcome":"timed-out","time":30000,' \
              '"timeExtra":3020,"word":12,"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":2,' \
              '"type":"round_start"},{"word":26,"type":"pick_stripe"},{"outcome":"guessed","time":27966,' \
              '"timeExtra":0,"word":26,"type":"stripe_outcome"},{"word":27,"type":"pick_stripe"},' \
              '{"outcome":"timed-out","time":2034,"timeExtra":723,"word":27,"type":"stripe_outcome"},' \
              '{"type":"finish_round"},{"from":2,"to":0,"type":"round_start"},{"word":23,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":14737,"timeExtra":0,"word":23,"type":"stripe_outcome"},{"word":41,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":13909,"timeExtra":0,"word":41,' \
              '"type":"stripe_outcome"},{"word":0,"type":"pick_stripe"},{"outcome":"guessed","time":1354,' \
              '"timeExtra":2892,"word":0,"type":"stripe_outcome"},{"type":"finish_round"},{"from":0,"to":2,' \
              '"type":"round_start"},{"word":10,"type":"pick_stripe"},{"outcome":"guessed","time":5022,"timeExtra":0,' \
              '"word":10,"type":"stripe_outcome"},{"word":31,"type":"pick_stripe"},{"outcome":"guessed","time":7016,' \
              '"timeExtra":0,"word":31,"type":"stripe_outcome"},{"word":27,"type":"pick_stripe"},' \
              '{"outcome":"guessed","time":4591,"timeExtra":0,"word":27,"type":"stripe_outcome"},{"word":18,' \
              '"type":"pick_stripe"},{"outcome":"guessed","time":6772,"timeExtra":0,"word":18,' \
              '"type":"stripe_outcome"},{"word":25,"type":"pick_stripe"},{"outcome":"guessed","time":6599,' \
              '"timeExtra":2634,"word":25,"type":"stripe_outcome"},{"type":"finish_round"},{"from":1,"to":0,' \
              '"type":"round_start"},{"word":19,"type":"pick_stripe"},{"outcome":"guessed","time":4298,"timeExtra":0,' \
              '"word":19,"type":"stripe_outcome"},{"word":12,"type":"pick_stripe"},{"outcome":"guessed","time":6529,' \
              '"timeExtra":0,"word":12,"type":"stripe_outcome"},{"type":"finish_round"},{"time":1588672017209,' \
              '"aborted":false,"type":"end_game"}]}'
WORDS_ORIG_CORRECT_V1 = [u'жокей', u'перфорация', u'акр', u'проектировщик', u'флюктуация', u'кистень', u'идеализация',
                         u'обмывание', u'привыкание', u'скиф', u'окулист', u'преступница', u'дагестанец',
                         u'судопроизводство', u'скок', u'деревенщина', u'номинал', u'дренаж', u'пилорама', u'скалка',
                         u'ликбез', u'сплетница', u'перикард', u'одаренность', u'хотение', u'черносотенец',
                         u'пароксизм', u'голубятня', u'импровизатор', u'слепок', u'уникум', u'беглянка', u'гордец',
                         u'регистратура', u'огневик', u'уклонист', u'чернушка', u'распыление', u'метафизика',
                         u'летосчисление', u'выборка', u'осмотрительность', u'сальник', u'хакер', u'самоцвет']
SEEN_WORDS_TIME_CORRECT_V1 = {1: 15, 2: 10, 3: 17, 4: 49, 5: 17, 6: 17, 7: 20, 8: 5, 9: 14, 10: 5, 11: 11, 12: 40,
                              13: 18, 14: 4, 15: 8, 16: 7, 17: 30, 18: 7, 20: 18, 21: 7, 22: 20, 24: 6, 25: 9, 26: 28,
                              27: 8, 28: 11, 29: 9, 30: 16, 31: 18, 32: 9, 33: 24, 34: 30, 35: 27, 36: 15, 37: 13,
                              38: 13, 39: 12, 40: 5, 41: 14, 42: 15, 43: 5, 44: 8}
WORDS_OUTCOME_CORRECT_V1 = {0: 'guessed', 1: 'guessed', 2: 'guessed', 3: 'guessed', 4: 'guessed', 5: 'guessed',
                            6: 'guessed', 7: 'guessed', 8: 'guessed', 9: 'guessed', 10: 'guessed', 11: 'guessed',
                            12: 'guessed', 13: 'guessed', 14: 'guessed', 15: 'guessed', 16: 'guessed',
                            17: 'guessed', 18: 'guessed', 19: 'guessed', 20: 'guessed', 21: 'guessed',
                            22: 'guessed', 23: 'guessed', 24: 'guessed', 25: 'guessed', 26: 'guessed',
                            27: 'guessed', 28: 'guessed', 29: 'guessed', 30: 'guessed', 31: 'guessed',
                            32: 'guessed', 33: 'guessed', 34: 'guessed', 35: 'guessed', 36: 'guessed',
                            37: 'guessed', 38: 'guessed', 39: 'guessed', 40: 'guessed', 41: 'guessed',
                            42: 'guessed', 43: 'guessed', 44: 'guessed'}
EXPLAINED_AT_ONCE_CORRECT_V1 = [False, True, True, True, False, True, True, True, True, True, True, True, False, True,
                                True, True, True, False, True, False, False, True, True, False, False, True, True,
                                False, True, True, True, False, True, True, True, False, True, True, True, False, True,
                                True, True, True, True]
EXPLAINED_PAIR_CORRECT_V1 = {1: (2, 1), 2: (1, 2), 3: (0, 1), 4: (2, 1), 5: (1, 0), 6: (0, 1), 7: (0, 2), 8: (1, 2),
                             9: (2, 0), 10: (0, 2), 11: (1, 2), 12: (1, 0), 13: (1, 2), 14: (1, 0), 15: (2, 0),
                             16: (2, 0), 17: (2, 1), 18: (0, 2), 20: (0, 2), 21: (2, 1), 22: (1, 0), 24: (0, 2),
                             25: (0, 2), 26: (1, 2), 27: (0, 2), 28: (1, 0), 29: (1, 0), 30: (0, 2), 31: (0, 2),
                             32: (0, 2), 33: (1, 0), 34: (0, 1), 35: (2, 0), 36: (2, 1), 37: (2, 0), 38: (0, 2),
                             39: (2, 1), 40: (1, 2), 41: (2, 0), 42: (2, 0), 43: (1, 2), 44: (0, 1)}
PLAYERS_NUM_CORRECT_V1 = 3
START_CORRECT_V1 = 1588681812202
STOP_CORRECT_V1 = 1588682817209
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
WORDS_ORIG_CORRECT_V2 = [u'цемент', u'кочегар', u'отгул', u'стопка', u'бросок', u'молочко', u'кислород', u'пуп',
                         u'смотритель', u'коэффициент', u'новинка', u'вакса', u'водичка', u'оборотень', u'перелом',
                         u'рукав', u'похолодание', u'карета', u'срок', u'жест', u'котлета', u'си', u'жид', u'ладья',
                         u'бутылка', u'электрон', u'дальность', u'пшеница', u'курс', u'патиссон', u'рожа', u'зуд',
                         u'певец', u'лгун', u'водопой', u'синица', u'комар', u'лотерея', u'съемка', u'гробница']
SEEN_WORDS_TIME_CORRECT_V2 = {0: 14, 2: 6, 3: 4, 4: 6, 5: 6, 6: 3, 8: 13, 9: 7, 10: 4, 12: 8, 13: 5, 14: 5, 16: 8,
                              17: 6,
                              18: 4, 19: 4, 21: 13, 22: 8, 24: 9, 25: 5, 26: 3, 28: 3, 30: 10, 31: 5, 32: 3, 36: 7,
                              37: 5,
                              38: 9}
WORDS_OUTCOME_CORRECT_V2 = {0: 'guessed', 2: 'guessed', 3: 'guessed', 4: 'guessed', 5: 'guessed', 6: 'guessed',
                            8: 'guessed', 9: 'guessed', 10: 'guessed', 12: 'guessed', 13: 'guessed', 14: 'guessed',
                            16: 'guessed', 17: 'guessed', 18: 'guessed', 19: 'guessed', 20: 'removed', 21: 'guessed',
                            22: 'guessed', 24: 'guessed', 25: 'guessed', 26: 'guessed', 27: 'removed', 28: 'guessed',
                            30: 'guessed', 31: 'guessed', 32: 'guessed', 34: 'failed', 36: 'guessed', 37: 'guessed',
                            38: 'guessed'}
EXPLAINED_AT_ONCE_CORRECT_V2 = {0: True, 2: True, 3: True, 4: True, 5: True, 6: True, 8: True, 9: True, 10: True,
                                12: True,
                                13: True, 14: True, 16: True, 17: True, 18: True, 19: True, 21: True, 22: True,
                                24: True,
                                25: True, 26: True, 28: True, 30: True, 31: True, 32: True, 36: True, 37: True,
                                38: True}
EXPLAINED_PAIR_CORRECT_V2 = {0: (0, 1), 2: (1, 2), 3: (1, 2), 4: (1, 2), 5: (1, 2), 6: (1, 2), 8: (3, 0), 9: (3, 0),
                             10: (3, 0), 12: (1, 3), 13: (1, 3), 14: (1, 3), 16: (2, 0), 17: (2, 0), 18: (2, 0),
                             19: (2, 0), 21: (3, 1), 22: (3, 1), 24: (0, 3), 25: (0, 3), 26: (0, 3), 28: (2, 1),
                             30: (2, 1), 31: (2, 1), 32: (2, 1), 36: (0, 1), 37: (0, 1), 38: (0, 1)}
PLAYERS_NUM_CORRECT_V2 = 4
START_CORRECT_V2 = 1582568822018
STOP_CORRECT_V2 = 1582569410857


class LogParserTest(unittest2.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.parse_log_v1 = AddGameHandler().parse_log_v1
        self.parse_log_v2 = AddGameHandler().parse_log_v2
        self.post = AddGameHandler().post

    def testParseLogV1(self):
        words_orig, seen_words_time, words_outcome, explained_at_once, explained_pair, players_num, start, stop = \
            self.parse_log_v1(json.loads(TEST_LOG_V1))
        self.assertEqual(words_orig, WORDS_ORIG_CORRECT_V1)
        self.assertEqual(dict(seen_words_time), SEEN_WORDS_TIME_CORRECT_V1)
        self.assertEqual(words_outcome, WORDS_OUTCOME_CORRECT_V1)
        self.assertEqual(explained_at_once, EXPLAINED_AT_ONCE_CORRECT_V1)
        self.assertEqual(explained_pair, EXPLAINED_PAIR_CORRECT_V1)
        self.assertEqual(players_num, PLAYERS_NUM_CORRECT_V1)
        self.assertEqual(start, START_CORRECT_V1)
        self.assertEqual(stop, STOP_CORRECT_V1)

    def testParseLogV2(self):
        words_orig, seen_words_time, words_outcome, explained_at_once, explained_pair, players_num, start, stop = \
            self.parse_log_v2(json.loads(TEST_LOG_V2))
        self.assertEqual(words_orig, WORDS_ORIG_CORRECT_V2)
        self.assertEqual(dict(seen_words_time), SEEN_WORDS_TIME_CORRECT_V2)
        self.assertEqual(words_outcome, WORDS_OUTCOME_CORRECT_V2)
        self.assertEqual(explained_at_once, EXPLAINED_AT_ONCE_CORRECT_V2)
        self.assertEqual(explained_pair, EXPLAINED_PAIR_CORRECT_V2)
        self.assertEqual(players_num, PLAYERS_NUM_CORRECT_V2)
        self.assertEqual(start, START_CORRECT_V2)
        self.assertEqual(stop, STOP_CORRECT_V2)

    def testPostV1(self):
        game_id = json.loads(TEST_LOG_V1)['setup']['meta']['game.id']
        log = GameLog(json=TEST_LOG_V1, id=game_id)
        game_key = log.put().urlsafe()
        request = Request.blank('/internal/add_game_to_statistic')
        request.method = 'POST'
        request.body = 'game_key=' + game_key
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def testPostV2(self):
        log = GameLog(json=TEST_LOG_V2)
        game_key = log.put().urlsafe()
        request = Request.blank('/internal/add_game_to_statistic')
        request.method = 'POST'
        request.body = 'game_key=' + game_key
        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == '__main__':
    unittest2.main()
