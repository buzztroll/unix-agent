#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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

    def _make_fake_alert_message(self):
        alert_doc = {"somekey": "value",
                     'alert_timestamp': 10.0,
                     'subject': 'fake subject',
                     'message': 'some alert message'}
        return alert_doc


    def test_simple_alert(self):
        alert_doc = self._make_fake_alert_message()
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn)
        alerter.send()
        alerter.incoming_message()
        conn.send.assert_called_once_with(alert_doc)
        alerter.stop()
        self.assertEqual(alerter._sm._current_state, "COMPLETE")

    def test_alert_retransmission(self):
        timeout = 0.1
        alert_doc = self._make_fake_alert_message()
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.send()
        dcm_events.poll(timeblock=timeout*1.5)
        alerter.incoming_message()

        call = mock.call(alert_doc)
        self.assertGreaterEqual(conn.send.call_count, 2)
        self.assertEqual(conn.send.call_args_list[0], call)

    def test_twosends_two_acks(self):
        timeout = 0.1
        alert_doc = self._make_fake_alert_message()
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.send()
        dcm_events.poll(timeblock=timeout*1.5)
        call = mock.call(alert_doc)
        self.assertGreaterEqual(conn.send.call_count, 2)
        self.assertEqual(conn.send.call_args_list, [call, call])

    def test_stop_before_done(self):
        timeout = 0.1
        alert_doc = self._make_fake_alert_message()
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.send()
        alerter.stop()
        self.assertEqual(alerter._sm._current_state, "COMPLETE")

    def test_stop_before_send(self):
        timeout = 0.1
        alert_doc = self._make_fake_alert_message()
        conn = mock.Mock()
        alerter = alert_msg.AlertAckMsg(alert_doc, conn, timeout=timeout)
        alerter.stop()
        self.assertEqual(alerter._sm._current_state, "COMPLETE")
