import mock
import unittest

import dcm.agent.messaging.alert_msg as alert_msg
import dcm.agent.tests.utils.general as test_utils

from dcm.agent.events.globals import global_space as dcm_events


class TestAlertMessaging(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        pass

    def test_simple_alert(self):
        alert_doc = {"somekey": "value"}
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn)
        alerter.send()
        alerter.incoming_message()
        conn.send.assert_called_once_with(alert_doc)
        alerter.stop()
        self.assertEqual(alerter._sm._current_state, "COMPLETE")


    def test_alert_retransmission(self):
        timeout = 0.1
        alert_doc = {"somekey": "value"}
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.send()
        dcm_events.poll(timeblock=timeout*2.0)
        alerter.incoming_message()

        call = mock.call(alert_doc)
        self.assertEqual(conn.send.call_count, 2)
        self.assertEqual(conn.send.call_args_list, [call, call])

    def test_twosends_two_acks(self):
        timeout = 0.1
        alert_doc = {"somekey": "value"}
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.send()
        dcm_events.poll(timeblock=timeout*2.0)
        alerter.incoming_message()
        alerter.incoming_message()
        call = mock.call(alert_doc)
        self.assertEqual(conn.send.call_count, 2)
        self.assertEqual(conn.send.call_args_list, [call, call])

    def test_stop_before_done(self):
        timeout = 0.1
        alert_doc = {"somekey": "value"}
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.send()
        alerter.stop()
        self.assertEqual(alerter._sm._current_state, "COMPLETE")

    def test_stop_before_send(self):
        timeout = 0.1
        alert_doc = {"somekey": "value"}
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.stop()
        self.assertEqual(alerter._sm._current_state, "COMPLETE")
