import json
import logging
import os

import dcm.agent.connection.connection_interface as conniface
import dcm.agent.messaging.utils as utils
import dcm.agent.messaging.types as types
import dcm.agent.tests.utils.test_exceptions as test_exceptions


class TestConnectionFileIO(conniface.ConnectionInterface):

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

    def read(self):
        buf = self._reader.readline()
        j = json.loads(buf)
        return j

    def send(self, doc):
        buf = json.dumps(doc)
        self._writer.write(buf)
        self._writer.write(os.linesep)


class RequestRetransmission(object):
    def __init__(self):
        self.request_doc = None
        self._event_retrans_map = {
            types.MessageTypes.REQUEST: 0,
            types.MessageTypes.ACK: 0,
            types.MessageTypes.NACK: 0,
            "AFTER_REPLY_ACK": 0,
            types.MessageTypes.REPLY: 0}

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


class TestReplySuccessfullyAlways(conniface.ConnectionInterface):

    def __init__(self, reader, writer, reply_ignore_count=0,
                 retrans_requests=None):
        # a file like object that is full of command arguments. space separated
        self._readq = []
        self._reader = reader
        self._writer = writer
        self._reply_ignore_count = reply_ignore_count
        self._log = logging.getLogger(__name__)
        self._retrans = retrans_requests
        if self._retrans is None:
            self._retrans = []
        self._request_number = 0
        self._retrans_map = {}

    def read(self):
        try:
            if self._readq:
                msg = self._readq.pop()
                self._log.debug("Popped message " + str(msg))
                return msg
            buf = self._reader.readline().strip()
            if not buf:
                return None
                #raise exceptions.PerminateConnectionException(
                #    "The tester file ended")
            self._log.debug("read message " + buf)
            ba = buf.split()
            command = ba.pop(0)
            arguments = ba

            message_id = utils.new_message_id()
            request_id = utils.new_message_id()
            request_doc = {
                'type': types.MessageTypes.REQUEST,
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

            self._check_retrans(request_id, types.MessageTypes.REQUEST)

            return request_doc
        except Exception as ex:
            self._log.error(ex)

    def _check_retrans(self, request_id, event):
        if request_id in self._retrans_map:
            retrans = self._retrans_map[request_id]
            if retrans.should_retrans(event):
                self._readq.append(retrans.request_doc)

    def send(self, doc):
        t = doc['type']
        request_id = doc['request_id']
        self._check_retrans(request_id, t)
        if t == types.MessageTypes.ACK:
            # no reply required here
            return
        elif t == types.MessageTypes.NACK:
            # no reply required here
            return
        elif t == types.MessageTypes.REPLY:
            payload = doc['payload']
            self._writer.write(json.dumps(payload))
            self._writer.flush()

            if self._reply_ignore_count == 0:
                # we must ACK the reply
                reply_ack = {
                    "type": types.MessageTypes.ACK,
                    "request_id": doc["request_id"],
                    "message_id": doc["message_id"],
                }
                self._readq.append(reply_ack)
            else:
                self._reply_ignore_count -= 1
            self._check_retrans(request_id, "AFTER_REPLY_ACK")
        else:
            raise test_exceptions.AgentTestException(
                "type %s should never happen" % t)
