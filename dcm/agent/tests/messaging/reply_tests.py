import mock
import unittest
import time
from dcm.agent.messaging import exceptions

import dcm.agent.messaging.reply as reply
import dcm.agent.messaging.states as states
import dcm.agent.messaging.types as types


class TestRequesterStandardPath(unittest.TestCase):

    def test_reply_ack_simple(self):

        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, {})
        reply_rpc.ack(None, None, None, None, None, None)
        reply_rpc.reply(reply_payload)

        reply_doc = {"type": types.MessageTypes.ACK,
                     "request_id": request_id,
                     "message_id": message_id,
                     }
        reply_rpc.incoming_message(reply_doc)
        reply_listener.message_done.assert_called_once_with(reply_rpc)

        self.assertEqual(conn.send.call_count, 2)

        (param_list, keywords) = conn.send.call_args_list[0]
        ack_doc = param_list[0]

        self.assertEqual(ack_doc["type"], types.MessageTypes.ACK)
        self.assertEqual(ack_doc["request_id"], request_id)
        self.assertEqual(ack_doc["message_id"], message_id)

        (param_list, keywords) = conn.send.call_args_list[1]
        reply_doc = param_list[0]

        self.assertTrue('message_id' in reply_doc)
        self.assertTrue('request_id' in reply_doc)
        self.assertTrue('type' in reply_doc)
        self.assertEqual(reply_doc['type'], types.MessageTypes.REPLY)
        self.assertEqual(reply_doc['payload'], reply_payload)

    def test_reply_skip(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}
        incoming_message = {"incoming": "info"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, incoming_message)
        reply_rpc.reply(reply_payload)

        reply_doc = {"type": types.MessageTypes.ACK,
                     "request_id": request_id,
                     "message_id": message_id,
                     "payload": reply_payload
                     }
        reply_rpc.incoming_message(reply_doc)
        reply_listener.message_done.assert_called_once_with(reply_rpc)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        self.assertTrue('message_id' in send_doc)
        self.assertTrue('request_id' in send_doc)
        self.assertTrue('type' in send_doc)
        self.assertEqual(send_doc['type'], types.MessageTypes.REPLY)
        self.assertEqual(send_doc['payload'], reply_payload)
        self.assertEqual(conn.send.call_count, 1)

    def test_request_retrans_before_ack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, reply_payload)
        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.incoming_message(request_retrans_doc)
        reply_rpc.ack(None, None, None, None, None, None)

    def test_request_retrans_after_ack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, reply_payload)
        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.ack(None, None, None, None, None, None)
        reply_rpc.incoming_message(request_retrans_doc)

        self.assertEqual(conn.send.call_count, 2)

    def test_request_retrans_after_reply(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, reply_payload)
        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.reply(reply_payload)
        reply_rpc.incoming_message(request_retrans_doc)

        self.assertEqual(conn.send.call_count, 2)

        reply_doc = {"type": types.MessageTypes.ACK,
                     "request_id": request_id,
                     "message_id": message_id,
                     }
        reply_rpc.incoming_message(reply_doc)

    def test_request_nack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, reply_payload)
        reply_rpc.nak({})

    def test_reply_ack_timeout(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}
        incoming_message = {"incoming": "info"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, incoming_message,
            timeout=1)
        reply_rpc.reply(reply_payload)

        reply_doc = {"type": types.MessageTypes.ACK,
                     "request_id": request_id,
                     "message_id": message_id,
                     "payload": reply_payload
                     }
        time.sleep(1.1)
        reply_rpc.incoming_message(reply_doc)
        reply_listener.message_done.assert_called_once_with(reply_rpc)
        self.assertEqual(conn.send.call_count, 2)

    def test_request_nack_lost_retrans_after_nack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, conn, request_id, message_id, reply_payload)
        reply_rpc.nak({})

        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.incoming_message(request_retrans_doc)

        self.assertEqual(conn.send.call_count, 2)

    def tests_just_for_coverage(self):
        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}
        reply_rpc = reply.ReplyRPC(
            None, None, request_id, message_id, reply_payload)
        reply_doc = {
                 "request_id": request_id,
                 "message_id": message_id,
         }
        self.assertRaises(exceptions.MissingMessageParameterException,
                          reply_rpc.incoming_message, reply_doc)
        reply_doc['type'] = 'nothing'
        self.assertRaises(exceptions.InvalidMessageParameterValueException,
                          reply_rpc.incoming_message, reply_doc)

        reply_rpc._sm.mapping_to_digraph()

