import unittest

from google.appengine.ext import testbed

from objects.pin_number import PinNumber
import mox
import time

TEST_KEY = "test key"
TEST2_KEY = "another test key"


class PinNumberTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_generate_retrive_pin(self):
        pin_string = PinNumber.generate(TEST_KEY)
        self.assertEqual(len(pin_string), 8)
        pin = PinNumber.retrive(pin_string)
        self.assertEqual(pin.data_key, TEST_KEY)

    def test_auto_free(self):
        pin_string = PinNumber.generate(TEST_KEY)
        pin = PinNumber.retrive(pin_string, key=TEST_KEY, free=True)
        self.assertFalse(pin.used)
        pin = PinNumber.retrive(pin_string)
        self.assertFalse(pin.used)
        pin_string = PinNumber.generate(TEST_KEY)
        pin = PinNumber.retrive(pin_string, key=TEST2_KEY, free=True)
        self.assertIsNone(pin)
        pin = PinNumber.retrive(pin_string)
        self.assertTrue(pin.used)

    def test_reuse_after_removal(self):
        pin_string = PinNumber.generate(TEST_KEY)
        pin = PinNumber.retrive(pin_string)
        self.assertTrue(pin.used)
        pin.free()
        self.assertFalse(pin.used)
        PinNumber.generate(TEST_KEY)
        self.assertEqual(len(PinNumber.query().fetch()), 1)
        PinNumber.generate(TEST_KEY)
        self.assertEqual(len(PinNumber.query().fetch()), 2)

    def test_reuse_expired(self):
        m = mox.Mox()
        m.StubOutWithMock(time, 'time')
        time.time().MultipleTimes().AndReturn(0)
        m.ReplayAll()
        PinNumber.generate(TEST_KEY, lifetime=10)
        PinNumber.generate(TEST_KEY)
        m.VerifyAll()
        self.assertEqual(len(PinNumber.query().fetch()), 2)
        m.StubOutWithMock(PinNumber, 'time')
        PinNumber.time().MultipleTimes().AndReturn(11)
        m.ReplayAll()
        PinNumber.generate(TEST_KEY)
        m.VerifyAll()
        m.UnsetStubs()
        self.assertEqual(len(PinNumber.query().fetch()), 2)

    def test_bad_pins(self):
        pin_string = PinNumber.generate(TEST_KEY)
        bad_string = str(int(pin_string) + 1000)
        self.assertIsNone(PinNumber.retrive("101"))
        self.assertIsNone(PinNumber.retrive("axbc"))
        self.assertIsNone(PinNumber.retrive(bad_string))

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()
