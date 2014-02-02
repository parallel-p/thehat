import unittest
import mox

from google.appengine.ext import testbed
from google.appengine.ext import ndb


from objects.pin_number import PinNumber, PinNumberData
import time

TEST_KEY = "test key"
TEST_DATA = "test data"
TEST2_KEY = "another test key"
TEST2_DATA = "another test data"


class PinNumberTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_generate_retrive_pin(self):
        pin_string = PinNumber.generate(TEST_KEY, TEST_DATA)
        self.assertEqual(len(pin_string), 8)
        pin = PinNumber.retrive(pin_string)
        self.assertEqual(pin.data_key, TEST_KEY)
        self.assertEqual(pin.data, TEST_DATA)

    def test_auto_free(self):
        pin_string = PinNumber.generate(TEST_KEY, TEST_DATA)
        pin = PinNumber.retrive(pin_string, key=TEST_KEY, free=True)
        self.assertFalse(pin.used)
        pin = PinNumber.retrive(pin_string)
        self.assertFalse(pin.used)
        pin_string = PinNumber.generate(TEST_KEY, TEST_DATA)
        pin = PinNumber.retrive(pin_string, key=TEST2_KEY, free=True)
        self.assertIsNone(pin)
        pin = PinNumber.retrive(pin_string)
        self.assertTrue(pin.used)

    def test_reuse_after_removal(self):
        pin_string = PinNumber.generate(TEST_KEY, TEST_DATA)
        pin = PinNumber.retrive(pin_string)
        self.assertTrue(pin.used)
        pin.free()
        self.assertFalse(pin.used)
        PinNumber.generate(TEST_KEY, TEST_DATA)
        self.assertEqual(len(PinNumber.query().fetch()), 1)
        PinNumber.generate(TEST_KEY, TEST_DATA)
        self.assertEqual(len(PinNumber.query().fetch()), 2)

    def test_reuse_expired(self):
        m = mox.Mox()
        m.StubOutWithMock(time, 'time')
        time.time().MultipleTimes().AndReturn(0)
        m.ReplayAll()
        PinNumber.generate(TEST_KEY, data=TEST_DATA, lifetime=10)
        PinNumber.generate(TEST_KEY, data=TEST_DATA)
        m.VerifyAll()
        self.assertEqual(len(PinNumber.query().fetch()), 2)
        m.StubOutWithMock(PinNumber, 'time')
        PinNumber.time().MultipleTimes().AndReturn(11)
        m.ReplayAll()
        PinNumber.generate(TEST_KEY, data=TEST_DATA)
        m.VerifyAll()
        m.UnsetStubs()
        self.assertEqual(len(PinNumber.query().fetch()), 2)

    def test_bad_pins(self):
        pin_string = PinNumber.generate(TEST_KEY, TEST_DATA)
        bad_string = str(int(pin_string) + 1000)
        self.assertIsNone(PinNumber.retrive("101"))
        self.assertIsNone(PinNumber.retrive("axbc"))
        self.assertIsNone(PinNumber.retrive(bad_string))

    def test_descendants_removal(self):
        pin_string = PinNumber.generate(TEST_KEY, TEST_DATA)
        pin = PinNumber.retrive(pin_string)
        PinNumberData(parent=pin.key).put()
        self.assertEqual(len(PinNumberData.query(ancestor=pin.key).fetch()), 1)
        pin.free()
        self.assertEqual(len(PinNumberData.query(ancestor=pin.key).fetch()), 0)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()
