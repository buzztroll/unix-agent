import json
import threading
from wsgiref.simple_server import make_server
from dcm.agent import config
from dcm.agent.messaging import request, states, utils
import uuid
import sys
from ws4py.websocket import WebSocket
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication

from dcm.agent.events import global_space as dcm_events


class ServerEvent(object):
    CLOSED = "CLOSED"
    INCOMING_MESSAGE = "INCOMING_MESSAGE"
    REQUEST_COMPLETE = "REQUEST_COMPLETE"


class ServerState(object):
    WAITING_FOR_FIRST = "WAITING_FOR_FIRST"
    INITIALIZING = "INITIALIZING"
    UPGRADING = "UPGRADING"
    WAITING_FOR_SECOND = "WAITING_FOR_SECOND"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"


_g_event = threading.Event()
_g_rc = None
_g_message = None


def test_done(rc, message):
    global _g_event
    global _g_rc
    global _g_message

    _g_rc = rc
    _g_message = message
    _g_event.set()
    print message
    sys.exit(rc)


class FakeAgentManager(object):

    def __init__(self):
        self._sm = states.StateMachine(ServerState.WAITING_FOR_FIRST)
        self.conf = config.AgentConfig([])
        self.conf.test_skip_handshake = True
        self.agent_id = str(uuid.uuid4()).split("-")[0]
        self._lock = threading.RLock()
        self._req_RPC = None
        self.setup_states()
        self.expected_version = sys.argv[1]

    def set_connection(self, conn):
        self._conn = conn

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    @utils.class_method_sync
    def ws_closed(self):
        self._sm.event_occurred(ServerEvent.CLOSED)

    #@utils.class_method_sync
    def message_done(self):
        print "request done"
        self._sm.event_occurred(ServerEvent.REQUEST_COMPLETE)

    @utils.class_method_sync
    def incoming_message(self, incoming_doc):
        print "incoming message"
        self._sm.event_occurred(ServerEvent.INCOMING_MESSAGE, msg=incoming_doc)

    def get_handshake_doc(self):
        doc = {
            "agentID": self.agent_id,
            "cloudId": 1,
            "customerId": 200,
            "regionId": "us-east-1",
            "zoneId": None,
            "serverId": "testserver",
            "serverName": "testserver",
            "mountPoint": "/mnt",
            "pl": None,
            "version": "0.9.0"
        }
        handshake_doc = {}
        handshake_doc["handshake"] = doc
        handshake_doc["return_code"] = 200
        handshake_doc["message"] = "Successful handshake from fake agent " \
                                   "manager"
        return handshake_doc

    def _sm_first_handshake(self, msg=None):
        message_dict = json.loads(msg)
        self._first_agent_version = message_dict['version']
        print "First agent version is %s" % self._first_agent_version

        self._conn.send(self.get_handshake_doc())

        doc = {
            "command": "initialize",
            "arguments": {"cloudId": "3",
                          "customerId": 100L,
                          "regionId": None,
                          "zoneId": None,
                          "serverId": self.agent_id,
                          "serverName": "testmachine",
                          "encryptedEphemeralFsKey": None}}

        self._req_RPC = request.RequestRPC(doc, self._conn, self.agent_id,
                                           reply_callback=self.message_done)
        self._req_RPC.send()

    def _sm_initialize_completed_send_upgrade(self, msg=None):
        short_version = self.expected_version.split("-")[0]
        doc = {
            "command": "upgrade",
            "arguments": {"newVersion": short_version,
                          "url": "file:////agent/bin/upgrader.py",
                          "args":
                              ["file:////agent/bin/installer.sh",
                               sys.argv[2]]}}
        self._req_RPC = request.RequestRPC(doc, self._conn, self.agent_id,
                                           reply_callback=self.message_done)
        self._req_RPC.send()

    def _sm_outstanding_request_msg(self, msg=None):
        print msg
        self._req_RPC.incoming_message(json.loads(msg))

    def _sm_upgrade_done(self):
        print "The upgrade completed nicely"

    def _sm_upgrade_closed(self):
        print "The upgrade close but still may be working"

    def _sm_failed(self):
        print "failed"
        test_done(1, "FAILED")

    def _sm_second_handshake(self, msg=None):
        print "second handshake is in"
        message_dict = json.loads(msg)
        self._second_agent_version = message_dict['version']
        print "Second agent version is %s" % self._first_agent_version
        self._conn.send(self.get_handshake_doc())
        if self._second_agent_version != self.expected_version:
            test_done(1, "The upgraded version does not seem correct.  "
                         "received %s but expected %s" %
                         (self._second_agent_version, self.expected_version))
        else:
            test_done(0, "Went from version %s to version %s" %
                         (self._first_agent_version,
                          self._second_agent_version))

    def setup_states(self):
        self._sm.add_transition(ServerState.WAITING_FOR_FIRST,
                                ServerEvent.INCOMING_MESSAGE,
                                ServerState.INITIALIZING,
                                self._sm_first_handshake)
        self._sm.add_transition(ServerState.WAITING_FOR_FIRST,
                                ServerEvent.CLOSED,
                                ServerState.FAILED,
                                self._sm_failed)
        self._sm.add_transition(ServerState.WAITING_FOR_FIRST,
                                ServerEvent.REQUEST_COMPLETE,
                                ServerState.FAILED,
                                self._sm_failed)

        self._sm.add_transition(ServerState.INITIALIZING,
                                ServerEvent.INCOMING_MESSAGE,
                                ServerState.INITIALIZING,
                                self._sm_outstanding_request_msg)
        self._sm.add_transition(ServerState.INITIALIZING,
                                ServerEvent.REQUEST_COMPLETE,
                                ServerState.UPGRADING,
                                self._sm_initialize_completed_send_upgrade)
        self._sm.add_transition(ServerState.INITIALIZING,
                                ServerEvent.CLOSED,
                                ServerState.FAILED,
                                self._sm_failed)

        self._sm.add_transition(ServerState.UPGRADING,
                                ServerEvent.INCOMING_MESSAGE,
                                ServerState.UPGRADING,
                                self._sm_outstanding_request_msg)
        self._sm.add_transition(ServerState.UPGRADING,
                                ServerEvent.REQUEST_COMPLETE,
                                ServerState.WAITING_FOR_SECOND,
                                self._sm_upgrade_done)
        self._sm.add_transition(ServerState.UPGRADING,
                                ServerEvent.CLOSED,
                                ServerState.WAITING_FOR_SECOND,
                                self._sm_upgrade_closed)

        self._sm.add_transition(ServerState.WAITING_FOR_SECOND,
                                ServerEvent.INCOMING_MESSAGE,
                                ServerState.COMPLETE,
                                self._sm_second_handshake)

        self._sm.add_transition(ServerState.COMPLETE,
                                ServerEvent.INCOMING_MESSAGE,
                                ServerState.COMPLETE,
                                None)

fake_am = FakeAgentManager()


class FakeServerWebsocket(WebSocket):

    def opened(self):
        print "opened connection"
        fake_am.set_connection(self)

    def closed(self, code, reason=None):
        print "Closed " + reason
        fake_am.ws_closed()

    def received_message(self, message):
        try:
            d = json.loads(message.data)
            if d['type'] == "LOG":
                return
        except Exception as ex:
            print ex
            pass
        try:
            fake_am.incoming_message(message.data)
        except Exception as ex:
            print ex
            raise

    def send(self, doc):
        msg = json.dumps(doc)
        super(FakeServerWebsocket, self).send(msg, False)


def make_this_server():

    server = make_server('', 9000, server_class=WSGIServer,
                         handler_class=WebSocketWSGIRequestHandler,
                         app=WebSocketWSGIApplication(
                             handler_cls=FakeServerWebsocket))
    server.initialize_websockets_manager()

    server.timeout = 1
    while not _g_event.isSet():
        server.handle_request()
        dcm_events.poll(timeblock=0.0)

    global _g_message
    global _g_rc
    print _g_message
    return _g_rc


if __name__ == "__main__":
    rc = make_this_server()
    sys.exit(rc)
