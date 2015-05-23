import json
import logging
import threading

import dcm.agent.connection.connection_interface as conniface
import dcm.agent.messaging.utils as utils
import dcm.agent.messaging.types as message_types
import dcm.agent.tests.utils.test_exceptions as test_exceptions

from dcm.agent.events import global_space as dcm_events


_g_logger = logging.getLogger(__name__)


class RequestRetransmission(object):
    def __init__(self):
        self.request_doc = None
        self._event_retrans_map = {
            message_types.MessageTypes.REQUEST: 0,
            message_types.MessageTypes.ACK: 0,
            message_types.MessageTypes.NACK: 0,
            message_types.MessageTypes.REPLY: 0}

    def set_retrans_event(self, event, count):
        if event not in self._event_retrans_map:
            raise Exception("This event doesnt exist")
        self._event_retrans_map[event] = count

    def should_retrans(self, event):
        if event not in self._event_retrans_map:
            raise Exception("This event doesnt exist")
        if self._event_retrans_map[event] < 1:
            return False
        self._event_retrans_map[event] -= 1
        return True

    def set_request_doc(self, doc):
        self.request_doc = doc


class TestConnection(conniface.ConnectionInterface):

    def __init__(self, reader, writer, reply_ignore_count=0,
                 retrans_requests=None):
        # a file like object that is full of command arguments. space separated
        self._reader = reader
        self._writer = writer
        self._reply_ignore_count = reply_ignore_count
        self._retrans = retrans_requests
        if self._retrans is None:
            self._retrans = []
        self._request_number = 0
        self._retrans_map = {}
        self._lock = threading.Lock()

    def _read_from_file(self):
        buf = self._reader.readline().strip()
        if not buf:
            return

        _g_logger.debug("read message " + buf)
        ba = buf.split()
        command = ba.pop(0)
        arguments = ba

        message_id = utils.new_message_id()
        request_id = utils.new_message_id()
        request_doc = {
            'type': message_types.MessageTypes.REQUEST,
            'request_id': request_id,
            'message_id': message_id,
            'payload': {'command': command, 'arguments': arguments}
        }

        # check for any retrans requests of this message
        if len(self._retrans) > self._request_number:
            rt = self._retrans[self._request_number]
            self._retrans_map[request_id] = rt
            rt.set_request_doc(request_doc)
        self._request_number += 1

        self._check_retrans(request_id, message_types.MessageTypes.REQUEST)
        dcm_events.register_callback(
            self.recv_obj.incoming_parent_q_message, args=[request_doc])

    def set_receiver(self, receive_object):
        """
        Read 1 packet from the connection.  1 complete json doc.
        """
        self.recv_obj = receive_object
        self._read_from_file()

    def incoming_parent_q_message(self, request_id, msg):
        self._read_from_file()
        self.recv_obj.incoming_parent_q_message(msg)

    def _check_retrans(self, request_id, event):
        if request_id in self._retrans_map:
            retrans = self._retrans_map[request_id]
            if retrans.should_retrans(event):
                dcm_events.register_callback(
                    self.incoming_parent_q_message,
                    args=[request_id, retrans.request_doc])

    def connect(self, receive_callback, handshake_manager):
        pass

    def close(self):
        pass

    def send(self, doc):
        with self._lock:
            t = doc['type']
            request_id = doc['request_id']
            _g_logger.debug("Fake conn sending " + t)
            self._check_retrans(request_id, t)
            if t == message_types.MessageTypes.ACK:
                # no reply required here
                return
            elif t == message_types.MessageTypes.NACK:
                # no reply required here
                return
            elif t == message_types.MessageTypes.REPLY:
                payload = doc['payload']
                self._writer.write(json.dumps(payload) + '\n')
                self._writer.flush()

                if self._reply_ignore_count == 0:
                    # we must ACK the reply
                    reply_ack = {
                        "type": message_types.MessageTypes.ACK,
                        "request_id": doc["request_id"],
                        "message_id": doc["message_id"],
                    }
                    dcm_events.register_callback(
                        self.incoming_parent_q_message,
                        args=[doc["request_id"], reply_ack])
                else:
                    self._reply_ignore_count -= 1
            else:
                raise test_exceptions.AgentTestException(
                    "type %s should never happen" % t)


class ReplyConnection(object):

    def __init__(self):
        pass

    def send(self, doc):
        dcm_events.register_callback(
            self._request.incoming_message, args=[doc])

    def set_request_side(self, request):
        self._request = request

    def close(self):
        pass


class RequestConnection(object):

    def __init__(self):
        pass

    def send(self, doc):
        self._rl.incoming_parent_q_message(doc)

    def set_request_listener(self, rl):
        self._rl = rl

    def close(self):
        pass
