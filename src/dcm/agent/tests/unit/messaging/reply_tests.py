import mock
import time
import nose

import dcm.agent.exceptions as exceptions
from dcm.agent.messaging import persistence
import dcm.agent.messaging.reply as reply
import dcm.agent.messaging.types as types
import dcm.agent.tests.utils.general as test_utils


class TestRequesterStandardPath(object):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.db = mock.Mock()

    def test_reply_ack_simple(self):

        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENT_ID", conn, request_id,
            {"request_id": request_id}, self.db)
        reply_rpc.ack(None, None, None)
        reply_rpc.reply(reply_payload)

        reply_doc = {"type": types.MessageTypes.ACK,
                     "request_id": request_id,
                     "message_id": message_id,
                     }
        reply_rpc.incoming_message(reply_doc)
        reply_listener.message_done.assert_called_once_with(reply_rpc)

        nose.tools.eq_(conn.send.call_count, 2)

        (param_list, keywords) = conn.send.call_args_list[0]
        ack_doc = param_list[0]

        nose.tools.eq_(ack_doc["type"], types.MessageTypes.ACK)
        nose.tools.eq_(ack_doc["request_id"], request_id)

        (param_list, keywords) = conn.send.call_args_list[1]
        reply_doc = param_list[0]

        nose.tools.ok_('message_id' in reply_doc)

        nose.tools.ok_('request_id' in reply_doc)
        nose.tools.ok_('type' in reply_doc)
        nose.tools.eq_(reply_doc['type'], types.MessageTypes.REPLY)
        nose.tools.eq_(reply_doc['payload'], reply_payload)

    def test_reply_skip(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}
        incoming_message = {"incoming": "info"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENTID",
            conn, request_id, incoming_message, self.db)
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
        nose.tools.ok_('message_id' in send_doc)
        nose.tools.ok_('request_id' in send_doc)
        nose.tools.ok_('type' in send_doc)
        nose.tools.eq_(send_doc['type'], types.MessageTypes.REPLY)
        nose.tools.eq_(send_doc['payload'], reply_payload)
        nose.tools.eq_(conn.send.call_count, 1)

    def test_request_retrans_before_ack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENTID",
            conn, request_id, reply_payload, self.db)
        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.incoming_message(request_retrans_doc)
        reply_rpc.ack(None, None, None)

    def test_request_retrans_after_ack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENTID",
            conn, request_id, reply_payload, self.db)
        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.ack(None, None, None)
        reply_rpc.incoming_message(request_retrans_doc)

        nose.tools.eq_(conn.send.call_count, 2)

    def test_request_retrans_after_reply(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENTID",
            conn, request_id, reply_payload, self.db)
        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.reply(reply_payload)
        reply_rpc.incoming_message(request_retrans_doc)

        nose.tools.eq_(conn.send.call_count, 2)

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
            reply_listener, "AGENTID",
            conn, request_id, reply_payload, self.db)
        reply_rpc.nak({})

    def test_reply_ack_timeout(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}
        incoming_message = {"incoming": "info"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENTID",
            conn, request_id, incoming_message, self.db,
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
        nose.tools.eq_(conn.send.call_count, 2)

    def test_request_nack_lost_retrans_after_nack(self):
        conn = mock.Mock()
        reply_listener = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}

        reply_rpc = reply.ReplyRPC(
            reply_listener, "AGENTID",
            conn, request_id, reply_payload, self.db)
        reply_rpc.nak({})

        request_retrans_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': reply_payload
        }
        reply_rpc.incoming_message(request_retrans_doc)

        nose.tools.eq_(conn.send.call_count, 2)

    def tests_just_for_coverage(self):
        request_id = "requestID"
        message_id = "messageID"
        reply_payload = {"reply": "payload"}
        reply_rpc = reply.ReplyRPC(
            None, "AGENTID", None, request_id, reply_payload, self.db)
        reply_doc = {
            "request_id": request_id,
            "message_id": message_id,
        }

        passed = False
        try:
            reply_rpc.incoming_message(reply_doc)
        except exceptions.MissingMessageParameterException:
            passed = True
        nose.tools.ok_(passed)

        passed = False
        reply_doc['type'] = 'nothing'
        try:
            reply_rpc.incoming_message(reply_doc)
        except exceptions.InvalidMessageParameterValueException:
            passed = True
        nose.tools.ok_(passed)

        reply_rpc._sm.mapping_to_digraph()


class TestRequestListener(object):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.db = persistence.SQLiteAgentDB(":memory:")

    def test_read_request(self):
        conn = mock.Mock()
        disp = mock.Mock()
        conf = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"

        request_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': {}
        }
        disp.incoming_request.return_value = None

        reply_listener = reply.RequestListener(conf, conn, disp, self.db)
        reply_listener.incoming_parent_q_message(request_doc)
        nose.tools.ok_(disp.incoming_request.called)

    def test_read_request_retrans_request(self):
        disp = mock.Mock()
        conn = mock.Mock()
        conf = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"

        request_doc = {
            'type': types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': {}
        }
        # just make sure that everything doesnt blow up on a repeated request
        reply_listener = reply.RequestListener(conf, conn, disp, self.db)
        reply_listener.incoming_parent_q_message(request_doc)
        reply_listener.incoming_parent_q_message(request_doc)

    def test_unknown_ack(self):
        disp = mock.Mock()
        conn = mock.Mock()
        conf = mock.Mock()

        request_id = "requestID"
        message_id = "messageID"

        ack_doc = {
            "type": types.MessageTypes.ACK,
            "request_id": request_id,
            "message_id": message_id,
            "payload": {}
        }

        reply_listener = reply.RequestListener(conf, conn, disp, self.db)
        reply_listener.incoming_parent_q_message(ack_doc)

        (param_list, keywords) = conn.send.call_args
        send_doc = param_list[0]
        nose.tools.ok_('type' in send_doc)
        nose.tools.eq_(send_doc['type'], types.MessageTypes.NACK)
