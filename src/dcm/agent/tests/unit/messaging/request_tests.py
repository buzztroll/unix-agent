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
import time
import unittest

import mock

import dcm.agent.logger as logger
import dcm.agent.messaging.request as request
import dcm.agent.messaging.states as states
import dcm.agent.messaging.types as types

from dcm.agent.events.globals import global_space as dcm_events


class TestRequesterStandardPath(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.clear_dcm_logging()

    def _validate_request_message(self, send_doc, doc):
        self.assertEqual(send_doc['payload'], doc)
        self.assertTrue('message_id' in send_doc)
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.REQUEST)

    def test_request_call_writes_request_message(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self._validate_request_message(send_doc, doc)

        self.assertEqual(conn.send.call_count, 1)

    def test_request_ack(self):

        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.ACK,
                     'message_id': send_doc['message_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual('REQUESTED', requester._sm._current_state)

    def test_requesting_reply(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.REPLY,
                     'message_id': send_doc['message_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual(states.RequesterStates.USER_CALLBACK,
                         requester._sm._current_state)

    def test_standard_path(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.ACK,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual('REQUESTED', requester._sm._current_state)

        reply_doc = {'type': types.MessageTypes.REPLY,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}

        requester.incoming_message(reply_doc)
        self.assertEqual(states.RequesterStates.USER_CALLBACK,
                         requester._sm._current_state)

        reply = requester.get_reply()
        requester.got_reply()
        self.assertEqual(reply, reply_doc)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self.assertEqual(reply_doc['message_id'], send_doc['message_id'])
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.ACK)

        requester.ack_sent_timeout()

    def test_standard_with_callback_path(self):

        self.called = False

        def reply_called(*args, **kwargs):
            self.called = True

        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(
            doc, conn, "XYZ", reply_callback=reply_called)
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.ACK,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual('REQUESTED', requester._sm._current_state)

        reply_doc = {'type': types.MessageTypes.REPLY,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}

        requester.incoming_message(reply_doc)

        while requester._sm._current_state !=\
                states.RequesterStates.ACK_SENT:
            dcm_events.poll()

        self.assertEqual(states.RequesterStates.ACK_SENT,
                         requester._sm._current_state)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self.assertEqual(reply_doc['message_id'], send_doc['message_id'])
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.ACK)

        requester.ack_sent_timeout()


class TestRequesterRetransmissionCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.clear_dcm_logging()

    def _validate_request_message(self, send_doc, doc):
        self.assertEqual(send_doc['payload'], doc)
        self.assertTrue('message_id' in send_doc)
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.REQUEST)

    def test_request_no_ack_timeout(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ", timeout=1)
        requester.send()
        dcm_events.poll(timeblock=1.5)

        self.assertGreater(conn.send.call_count, 1)

        (param_list, keywords) = conn.send.call_args
        self._validate_request_message(param_list[0], doc)
        requester.cleanup()

    def test_double_reply(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.ACK,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual('REQUESTED', requester._sm._current_state)

        reply_doc = {'type': types.MessageTypes.REPLY,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}

        requester.incoming_message(reply_doc)
        self.assertEqual(states.RequesterStates.USER_CALLBACK,
                         requester._sm._current_state)

        requester.incoming_message(reply_doc)
        self.assertEqual(states.RequesterStates.USER_CALLBACK,
                         requester._sm._current_state)

        reply = requester.get_reply()
        requester.got_reply()
        self.assertEqual(reply, reply_doc)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self.assertEqual(reply_doc['message_id'], send_doc['message_id'])
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.ACK)

        requester.ack_sent_timeout()

    def test_reply_after_ack(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.ACK,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual('REQUESTED', requester._sm._current_state)

        reply_doc = {'type': types.MessageTypes.REPLY,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}

        requester.incoming_message(reply_doc)
        self.assertEqual(states.RequesterStates.USER_CALLBACK,
                         requester._sm._current_state)

        requester.incoming_message(reply_doc)

        reply = requester.get_reply()
        requester.got_reply()
        self.assertEqual(reply, reply_doc)
        requester.incoming_message(reply_doc)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self.assertEqual(reply_doc['message_id'], send_doc['message_id'])
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.ACK)

        requester.ack_sent_timeout()
        requester.cleanup()

    def test_double_requested_ack(self):
        conn = mock.Mock()
        doc = {'amessage': 'foru'}

        requester = request.RequestRPC(doc, conn, "XYZ")
        requester.send()

        self.assertEqual(conn.send.call_count, 1)
        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]

        reply_doc = {'type': types.MessageTypes.ACK,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}
        requester.incoming_message(reply_doc)
        self.assertEqual('REQUESTED', requester._sm._current_state)
        requester.incoming_message(reply_doc)

        reply_doc = {'type': types.MessageTypes.REPLY,
                     'message_id': send_doc['message_id'],
                     'request_id': send_doc['request_id']}

        requester.incoming_message(reply_doc)
        self.assertEqual(states.RequesterStates.USER_CALLBACK,
                         requester._sm._current_state)

        reply = requester.get_reply()
        requester.got_reply()
        self.assertEqual(reply, reply_doc)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self.assertEqual(reply_doc['message_id'], send_doc['message_id'])
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.ACK)

        requester.ack_sent_timeout()
