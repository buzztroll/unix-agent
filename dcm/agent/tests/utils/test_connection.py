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


class TestReplySuccessfullyAlways(conniface.ConnectionInterface):

    def __init__(self, reader, writer, reply_ignore_count=0):
        # a file like object that is full of command arguments. space separated
        self._readq = []
        self._reader = reader
        self._writer = writer
        self._reply_ignore_count = reply_ignore_count
        self._log = logging.getLogger(__name__)

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
            return request_doc
        except Exception as ex:
            self._log.error(ex)

    def send(self, doc):
        t = doc['type']

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
            pass
        else:
            raise test_exceptions.AgentTestException(
                "type %s should never happen" % t)

