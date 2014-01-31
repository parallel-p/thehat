import unittest

from google.appengine.ext import testbed

from objects.pin_number import PinNumber
import mox

TEST_DATA = "test data"


class PinNumberTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def test_generate_retrive_pin(self):
        pin_string = PinNumber.generate(data=TEST_DATA)
        self.assertEqual(len(pin_string), 8)
        pin = PinNumber.retrive(pin_string)
        self.assertEqual(pin.data, TEST_DATA)

    def test_reuse_after_removal(self):
        pin_string = PinNumber.generate(data=TEST_DATA)
        pin = PinNumber.retrive(pin_string)
        self.assertTrue(pin.used)
        pin.free()
        self.assertFalse(pin.used)
        PinNumber.generate(data=TEST_DATA)
        self.assertEqual(len(PinNumber.query().fetch()), 1)
        PinNumber.generate(data=TEST_DATA)
        self.assertEqual(len(PinNumber.query().fetch()), 2)

    @unittest.skip("Can't mock up time function")
    def test_reuse_expired(self):
        m = mox.Mox()
        m.StubOutWithMock(PinNumber, 'time')
        PinNumber.time().AndReturn(0)
        m.ReplayAll()
        PinNumber.generate(data=TEST_DATA, lifetime=10)
        PinNumber.generate(data=TEST_DATA)
        m.VerifyAll()
        self.assertEqual(len(PinNumber.query().fetch()), 2)
        m.StubOutWithMock(PinNumber, 'time')
        PinNumber.time().AndReturn(11)
        m.ReplayAll()
        PinNumber.generate(data=TEST_DATA)
        m.VerifyAll()
        m.UnsetStubs()
        self.assertEqual(len(PinNumber.query().fetch()), 2)

    def tearDown(self):
        self.testbed.deactivate()


if __name__ == "__main__":
    unittest.main()
