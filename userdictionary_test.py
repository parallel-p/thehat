import unittest
import urllib
import urllib2
import json
from random import *
from time import *

'''
This is a program which will test creating of user's dictionary
'''

class TestWordsUpload(unittest.TestCase):
    def test_creation(self):
        for i in range(10):
            first_game = '''[{"word": "word_1", "version": 0, "active": 1}, {"word": "word2", "version": VERS, "active": 0}]'''
            cversion = randint(1, 10000)
            first_game = first_game.replace("VERS", str(cversion))
            data = {"json": first_game}
            data = urllib.urlencode(data)
            req = urllib2.Request('http://localhost:8080/udict/60/change/', data)
            response = urllib2.urlopen(req)
            # print(dir(response), response.read())
            self.assertTrue(int(response.read()) >= cversion)

class TestWordDownload(unittest.TestCase):
    def test_creation(self):
        for i in range(10):
            first_game = '''[{"word": "word_1", "version": 0, "active": 1}, {"word": "word2", "version": VERS, "active": 0}]'''
            cversion = randint(1, 10000)
            cuser = randint(1, 10000)
            first_game = first_game.replace("VERS", str(cversion))
            data = {"diff": first_game}
            data = urllib.urlencode(data)
            print('http://localhost:8080/udict/CUSER/change'.replace("CUSER", str(cuser)), data)
            req = urllib2.Request('http://localhost:8080/udict/CUSER/change/'.replace("CUSER", str(cuser)), data)
            urllib2.urlopen(req)
            print('http://localhost:8080/udict/CUSER/update/0'.replace('CUSER', str(cuser)))
            resp = urllib2.urlopen('http://localhost:8080/udict/CUSER/update/-1'.replace('CUSER', str(cuser)))
            self.assertTrue(resp.code == 200)


if __name__ == "__main__":
    unittest.main()
