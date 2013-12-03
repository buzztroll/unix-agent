import json
import os

import dcm.agent.connection as agent_connection
from dcm.agent.messaging import utils
import dcm.agent.messaging.types as types
import dcm.agent.tests.utils.test_exceptions as test_exceptions


class TestConnectionFileIO(agent_connection.ConnectionInterface):

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

    def read(self):
        buf = self._reader.readline()
        j = json.loads(buf)
        return j

    def write(self, doc):
        buf = json.dumps(doc)
        self._writer.write(buf)
        self._writer.write(os.linesep)


class TestReplySuccessfullyAlways(agent_connection.ConnectionInterface):

    def __init__(self, reader):
        # a file like object that is full of command arguments.  space separated
        self._readq = []
        self._reader = reader

    def read(self):
        if self._readq:
            return self._readq.pop()
        buf = self._reader.readline()
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

    def write(self, doc):
        t = doc['type']

        if t == types.MessageTypes.ACK:
            # no reply required here
            return
        elif t == types.MessageTypes.NACK:
            # no reply required here
            return
        elif t == types.MessageTypes.REPLY:
            # we must ACK the reply
            reply_ack = {
                "type": types.MessageTypes.REPLY,
                "request_id": doc["request_id"],
                     "message_id": doc["message_id"],
            }
            self._readq.append(reply_ack)
        else:
            raise test_exceptions.AgentTestException(
                "type %s should never happen" % t)

