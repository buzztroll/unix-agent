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
import datetime
import math
import mock
import time
import unittest

import dcm.agent.connection.websocket as websocket
import dcm.agent.handshake as handshake
import dcm.agent.tests.utils.general as test_utils

from dcm.agent.events.globals import global_space as dcm_events


def fake_incoming_message(incoming_doc):
    pass


class TestBackoff(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def run_with_connect_errors(
            self,
            backoff_seconds,
            max_backoff_seconds,
            run_time_seconds,
            conn_obj):

        class FakeHS(object):
            def get_send_document(self):
                ws.throw_error(Exception("just for tests"))
                return {}

            def incoming_document(self, incoming_doc):
                return handshake.HandshakeIncomingReply(
                    handshake.HandshakeIncomingReply.REPLY_CODE_SUCCESS)

        m = mock.Mock()
        conn_obj.return_value = m

        server_url = "wss://notreal.com"

        ws = websocket.WebSocketConnection(
            server_url,
            backoff_amount=int(backoff_seconds*1000),
            max_backoff=int(max_backoff_seconds*1000))

        ws.connect(fake_incoming_message, FakeHS())

        nw = datetime.datetime.now()
        done_time = nw + datetime.timedelta(seconds=run_time_seconds)
        while done_time > nw:
            remaining = done_time - nw
            dcm_events.poll(timeblock=remaining.total_seconds())
            nw = datetime.datetime.now()

        ws.close()
        return m

    @mock.patch('dcm.agent.connection.websocket._WebSocketClient')
    def test_no_retry(self, conn_obj):
        """Make sure that just 1 connect happens when waiting less than the
        backoff time"""
        m = mock.Mock()
        conn_obj.return_value = m

        backoff_seconds = 3.0
        max_backoff_seconds = backoff_seconds * 100.0  # just make a big number
        run_time_seconds = backoff_seconds / 2.0  # less then the back off

        m = self.run_with_connect_errors(
            backoff_seconds,
            max_backoff_seconds,
            run_time_seconds,
            conn_obj)

        self.assertEqual(1, m.connect.call_count)

    @mock.patch('dcm.agent.connection.websocket._WebSocketClient')
    def test_retry_connections(self, conn_obj):
        """Make sure reconnections happen"""
        m = mock.Mock()
        conn_obj.return_value = m

        initial_backoff_seconds = 0.5
        max_backoff_seconds = 600.0
        run_time_seconds = 5.0
        expected_backoff_count =\
            int(math.log(run_time_seconds / initial_backoff_seconds, 2))

        m = self.run_with_connect_errors(
            initial_backoff_seconds,
            max_backoff_seconds,
            run_time_seconds,
            conn_obj)

        self.assertLessEqual(expected_backoff_count-2, m.connect.call_count)
        self.assertGreaterEqual(expected_backoff_count+2, m.connect.call_count)

    @mock.patch('dcm.agent.connection.websocket._WebSocketClient')
    def test_retry_connections_never_more_than_max_back(self, conn_obj):
        m = mock.Mock()
        conn_obj.return_value = m

        initial_backoff_seconds = 5.0
        max_backoff_seconds = 0.1
        run_time_seconds = 3.0
        expected_backoff_count = run_time_seconds / max_backoff_seconds

        m = self.run_with_connect_errors(
            initial_backoff_seconds,
            max_backoff_seconds,
            run_time_seconds,
            conn_obj)

        self.assertGreaterEqual(expected_backoff_count, m.connect.call_count)

    @mock.patch('dcm.agent.connection.websocket._WebSocketClient')
    def test_force_backoff(self, conn_obj):

        # force the backoff to be longer than the max run time then make sure
        # that the connect is only called once
        backoff_seconds = 0.2
        max_backoff_seconds = backoff_seconds
        run_time_seconds = backoff_seconds * 10.0
        force_time = run_time_seconds + 1.0

        m = mock.Mock()
        conn_obj.return_value = m

        server_url = "wss://notreal.com"

        ws = websocket.WebSocketConnection(
            server_url,
            backoff_amount=int(backoff_seconds*1000),
            max_backoff=int(max_backoff_seconds*1000))

        def send_in_handshake():
            ws.event_incoming_message(
                {handshake.HandshakeIncomingReply.REPLY_KEY_FORCE_BACKOFF:
                 force_time,
                 'return_code':
                 handshake.HandshakeIncomingReply.REPLY_CODE_FORCE_BACKOFF})

        class FakeHS(object):
            def get_send_document(self):
                dcm_events.register_callback(send_in_handshake)
                return {}

            def incoming_document(self, incoming_doc):
                hs = handshake.HandshakeIncomingReply(
                    handshake.HandshakeIncomingReply.REPLY_CODE_FORCE_BACKOFF,
                    force_backoff=force_time)
                return hs

        ws.connect(fake_incoming_message, FakeHS())

        nw = datetime.datetime.now()
        done_time = nw + datetime.timedelta(seconds=run_time_seconds)
        while done_time > nw:
            remaining = done_time - nw
            dcm_events.poll(timeblock=remaining.total_seconds())
            nw = datetime.datetime.now()

        ws.close()

        self.assertEqual(1, m.connect.call_count)

    def test_backoff_object_ready_immediately(self):
        initial_backoff_second = 300.0
        max_backoff_seconds = initial_backoff_second
        backoff = websocket.Backoff(
            max_backoff_seconds,
            initial_backoff_second=initial_backoff_second)
        self.assertTrue(backoff.ready())

    def test_backoff_object_error_not_ready(self):
        initial_backoff_second = 300.0
        max_backoff_seconds = initial_backoff_second
        backoff = websocket.Backoff(
            max_backoff_seconds,
            initial_backoff_second=initial_backoff_second)
        backoff.error()
        self.assertFalse(backoff.ready())

    def test_backoff_object_error_wait_ready(self):
        initial_backoff_second = 0.05
        max_backoff_seconds = initial_backoff_second
        backoff = websocket.Backoff(
            max_backoff_seconds,
            initial_backoff_second=initial_backoff_second)
        backoff.error()
        time.sleep(initial_backoff_second)
        self.assertTrue(backoff.ready())

    def test_backoff_object_ready_after_many_errors_than_activity(self):
        initial_backoff_second = 0.05
        max_backoff_seconds = initial_backoff_second
        backoff = websocket.Backoff(
            max_backoff_seconds,
            initial_backoff_second=initial_backoff_second)
        backoff.error()
        backoff.error()
        backoff.error()
        backoff.error()
        backoff.error()
        backoff.error()
        self.assertFalse(backoff.ready())
        backoff.activity()
        self.assertTrue(backoff.ready())
