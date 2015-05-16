import datetime
import threading
import time
import unittest
import uuid

import dcm.agent.tests.utils.general as test_utils
import dcm.agent.events as events


class TestEventSpace(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def test_simple_callback(self):
        event_space = events.EventSpace()
        x_val = 1
        y_val = []
        apple_val = "sauce"

        def test_callback(x_param, y_param, apple_param=None):
            self.assertEqual(x_param, x_val)
            self.assertEqual(y_param, y_val)
            self.assertEqual(apple_param, apple_val)
            y_val.append("called")

        event_space.register_callback(test_callback,
                                      args=[x_val, y_val],
                                      kwargs={'apple_param': apple_val})

        event_space.poll(timeblock=0.0)
        self.assertEqual(len(y_val), 1)

    def test_callback_delay(self):
        """Make sure that the delayed callback is called second"""
        event_space = events.EventSpace()
        x_val = []

        def test_callback1(x_param):
            self.assertEqual(x_param, x_val)
            x_val.append(1)

        def test_callback2(x_param):
            self.assertEqual(x_param, x_val)
            x_val.append(2)

        d = 0.1
        event_space.register_callback(test_callback2, args=[x_val], delay=d)
        event_space.register_callback(test_callback1, args=[x_val])

        event_space.poll(timeblock=d*2.0)
        self.assertEqual(len(x_val), 2)
        self.assertEqual(x_val[0], 1)
        self.assertEqual(x_val[1], 2)

    def test_delay_before_calling(self):
        """Make sure that the delay happens"""
        event_space = events.EventSpace()
        x_val = []

        def test_callback1(x_param):
            self.assertEqual(x_param, x_val)
            x_val.append(datetime.datetime.now())

        d = 0.2
        event_space.register_callback(test_callback1, args=[x_val], delay=d)

        start = datetime.datetime.now()
        event_space.poll(timeblock=d+1.0)
        self.assertEqual(len(x_val), 1)
        self.assertGreater(x_val[0], start + datetime.timedelta(seconds=d))

    def test_shutdown_while_running(self):
        """shutdow" the event space with pending events, verify they are
        not called"""
        event_space = events.EventSpace()
        x_val = []

        def test_callback1(x_param):
            event_space.stop()

        def test_callback2(x_param):
            x_param.append(1)

        d = 0.1
        event_space.register_callback(test_callback2, args=[x_val], delay=d)
        event_space.register_callback(test_callback1, args=[x_val])

        event_space.poll(timeblock=d*2.0)
        self.assertEqual(len(x_val), 0)

    def test_cancel_a_callback(self):
        """cancel a callback and verify it did not run"""
        event_space = events.EventSpace()
        x_val = []
        d = 0.1

        def test_callback1(x_param):
            x_param.append(1)

        ub1 = event_space.register_callback(
            test_callback1, args=[x_val], delay=d)

        def test_callback2():
            x = event_space.cancel_callback(ub1)
            self.assertTrue(x)

        event_space.register_callback(test_callback2)

        event_space.poll(timeblock=d*2.0)
        self.assertEqual(len(x_val), 0)


    def test_cancel_already_run_callback(self):
        """cancel an already called callback and verify return code"""
        event_space = events.EventSpace()
        x_val = []
        d = 0.1

        def test_callback1(x_param):
            x_param.append(1)

        ub1 = event_space.register_callback(test_callback1, args=[x_val])
        event_space.poll(timeblock=d)
        self.assertEqual(len(x_val), 1)
        x = event_space.cancel_callback(ub1)
        self.assertFalse(x)

    def test_return_code(self):
        event_space = events.EventSpace()
        apple_val = "sauce"

        def test_callback():
            return apple_val

        ub = event_space.register_callback(test_callback)

        event_space.poll(timeblock=0.0)
        self.assertEqual(ub.get_rc(), apple_val)
        self.assertTrue(ub.has_run())
        self.assertIsNone(ub.get_exception())

    def test_return_code(self):
        event_space = events.EventSpace()
        exception_message = str(uuid.uuid4())

        def test_callback():
            raise Exception(exception_message)

        ub = event_space.register_callback(test_callback)

        event_space.poll(timeblock=0.0)
        self.assertIsNone(ub.get_rc())
        self.assertTrue(ub.has_run())
        self.assertEqual(exception_message, ub.get_exception().message)

    def test_wakeup_on_register(self):
        # test that callback happens when it is registered after the poll
        event_space = events.EventSpace()
        param = []
        start_time = []
        delay = 0.1

        def test_callback(param):
            param.append(datetime.datetime.now())

        def register_new_callback():
            time.sleep(delay)
            start_time.append(datetime.datetime.now())
            event_space.register_callback(test_callback, args=[param])

        t = threading.Thread(target=register_new_callback)
        t.start()
        poll_time = datetime.datetime.now()
        event_space.poll(timeblock=delay * 2)
        self.assertEqual(len(param), 1)
        self.assertGreater(start_time[0], poll_time)
        t.join()

    def register_events_in_callback(self):
        event_space = events.EventSpace()
        param = []

        def test_callback1(param):
            param.append(1)

        def test_callback2(param):
            param.append(2)

        def test_callback3(param):
            event_space.register_callback(test_callback1, args=[param])
            event_space.register_callback(test_callback2, args=[param])

        event_space.register_callback(test_callback3, args=[param])

        event_space.poll(0.1)

        self.assertEqual(len(param), 2)
        self.assertIn(1, param)
        self.assertIn(2, param)
