#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================

import errno
import json
import logging
import Queue
import socket
import threading
import datetime

import ws4py.client.threadedclient as ws4py_client
from dcm.agent import exceptions
from dcm.agent.messaging import states

import dcm.agent.messaging.utils as utils
import dcm.agent.utils as agent_utils
import dcm.agent.parent_receive_q as parent_receive_q


_g_logger = logging.getLogger(__name__)


class WsConnEvents:
    POLL = "POLL"
    CONNECT_TIMEOUT = "CONNECT_TIMEOUT"
    GOT_HANDSHAKE = "GOT_HANDSHAKE"
    ERROR = "ERROR"
    CLOSE = "CLOSE"


class WsConnStates:
    WAITING = "WAITING"
    HANDSHAKING = "HANDSHAKING"
    OPEN = "OPEN"
    DONE = "DONE"


class RepeatQueue(object):

    def __init__(self):
        self._q = Queue.Queue()
        self._lock = threading.RLock()
        self._message_id_set = set()
        self._request_id_count = {}

    def put(self, item, block=True, timeout=None):
        self._lock.acquire()
        try:
            try:
                if 'message_id' in item:
                    message_id = item['message_id']
                    if message_id in self._message_id_set:
                        _g_logger.info("Skipping sending a retransmission "
                                       "of message id %s" % message_id)
                        return
                    else:
                        _g_logger.debug("Adding the message with id %s " %
                                        message_id)
                    self._message_id_set.add(message_id)
                if 'request_id' in item:
                    request_id = item['request_id']
                    if request_id not in self._request_id_count:
                        self._request_id_count[request_id] = 0
                    self._request_id_count[request_id] += 1

                    if self._request_id_count[request_id] > 500:
                        msg = "TOO MANY MESSAGES FOR %s!" % request_id
                        _g_logger.error(msg)
                        agent_utils.log_to_dcm(logging.ERROR, msg)
                        agent_utils.build_assertion_exception(_g_logger, msg)
                        return
            except Exception as ex:
                _g_logger.warn("Exception checking if message is a retrans "
                               "%s" % ex.message)
            return self._q.put(item, block=block, timeout=timeout)
        finally:
            self._lock.release()

    def get(self, block=True, timeout=None):
        self._lock.acquire()
        try:
            item = self._q.get(block=block, timeout=timeout)
            try:
                if 'message_id' in item:
                    if item['message_id'] in self._message_id_set:
                        self._message_id_set.remove(item['message_id'])
            except Exception as ex:
                _g_logger.info("Exception checking if message has an id "
                               "%s" % ex.message)
            return item
        finally:
            self._lock.release()

    def task_done(self):
        return self._q.task_done()


class _WebSocketClient(ws4py_client.WebSocketClient):

    def __init__(self, manager, url, receive_queue, protocols=None,
                 extensions=None,
                 heartbeat_freq=None, ssl_options=None, headers=None):
        ws4py_client.WebSocketClient.__init__(
            self, url, protocols=protocols, extensions=extensions,
            heartbeat_freq=heartbeat_freq, ssl_options=ssl_options,
            headers=headers)
        _g_logger.info("Attempting to connect to %s" % url)

        self.receive_queue = receive_queue
        self.manager = manager
        self._url = url
        self._complete_handshake = False
        self._handshake_reply = None
        self._dcm_closed_called = False

    def send_handshake(self, handshake):
        _g_logger.debug("Sending handshake")
        self.send(handshake)

    def opened(self):
        _g_logger.debug("Web socket %s has been opened" % self._url)

    def closed(self, code, reason=None):
        _g_logger.info("Web socket %s has been closed %d %s"
                       % (self._url, code, reason))
        _g_logger.debug("Sending error event to connection manager.")
        self.manager.throw_error(Exception(
            "Connection unexpectedly closed: %d %s" % (code, reason)))

    def close(self, code=1000, reason=''):
        self._dcm_closed_called = True
        return ws4py_client.WebSocketClient.close(
            self, code=code, reason=reason)

    def received_message(self, m):
        _g_logger.debug("WS message received " + m.data)
        if not self._complete_handshake:
            _g_logger.debug("Handshake received")
            self._complete_handshake = True
            json_doc = json.loads(m.data)
            self._handshake_reply = json_doc
            self.manager.event_handshake_received(json_doc)
        else:
            _g_logger.debug("New message received")
            json_doc = json.loads(m.data)
            self.receive_queue.put(json_doc)


class WebSocketConnection(threading.Thread):

    def __init__(self, server_url, backoff_amount=5000, max_backoff=300000,
                 heartbeat=None):
        super(WebSocketConnection, self).__init__()
        self._send_queue = RepeatQueue()
        self._ws_manager = None
        self._server_url = server_url
        self._cond = threading.Condition()
        self._done_event = threading.Event()
        self._backoff_time = 1.0
        self._backoff_amount = float(backoff_amount) / 1000.0
        self._max_backoff = float(max_backoff) / 1000.0
        self._total_errors = 0
        self._errors_since_success = 0
        self._sm = states.StateMachine(WsConnStates.WAITING)
        self._setup_states()
        self.handshake_observer = None
        self._next_connect_time = datetime.datetime.now()
        self._heartbeat_freq = heartbeat

    @utils.class_method_sync
    def connect(self, receive_object, handshake_observer, handshake_doc):
        self._receive_queue = parent_receive_q.get_master_receive_queue(
            receive_object, str(self))
        self._hs_string = json.dumps(handshake_doc)
        self.handshake_observer = handshake_observer
        self.start()
        self._backoff_time = None

    @utils.class_method_sync
    def send(self, doc):
        _g_logger.debug("Adding a message to the send queue")
        self._send_queue.put(doc)
        self._cond.notify()

    @utils.class_method_sync
    def close(self):
        _g_logger.debug("Websocket connection closed.")
        self.event_close()

    @utils.class_method_sync
    def run(self):
        while not self._done_event.is_set():
            try:
                self._sm.event_occurred(WsConnEvents.POLL)
                _g_logger.debug("Waiting %s for the next poll event." %
                                str(self._backoff_time))
                self._cond.wait(self._backoff_time)
            except Exception as ex:
                _g_logger.exception("The ws connection poller loop had "
                                    "an unexpected exception.")
                self._throw_error(ex)

    #########
    # incoming events
    #########
    @utils.class_method_sync
    def event_close(self):
        self._sm.event_occurred(WsConnEvents.CLOSE)

    @utils.class_method_sync
    def event_handshake_received(self, incoming_handshake):
        self._sm.event_occurred(WsConnEvents.GOT_HANDSHAKE,
                                incoming_handshake=incoming_handshake)
        self._errors_since_success = 0

    @utils.class_method_sync
    def event_error(self, exception=None):
        self._sm.event_occurred(WsConnEvents.ERROR)
        _g_logger.error(
            "State machine received an exception %s" % str(exception))

    @utils.class_method_sync
    def _register_connect(self):
        self._sm.event_occurred(WsConnEvents.CONNECT_TIMEOUT)

    def _increase_backoff(self):
        if self._backoff_time is None:
            self._backoff_time = 0.0
        self._backoff_time = self._backoff_time + self._backoff_amount
        if self._backoff_time > self._max_backoff:
            self._backoff_time = self._max_backoff
        self._total_errors += 1
        self._errors_since_success += 1
        self._next_connect_time = datetime.datetime.now() +\
            datetime.timedelta(microseconds=int(self._backoff_time*1000000))
        self._cond.notify()

    def _throw_error(self, exception, notify=True):
        _g_logger.warning("throwing error %s" % str(exception))
        parent_receive_q.register_user_callback(self.event_error,
                                                {"exception": exception})
        if notify:
            self._cond.notify()

    def throw_error(self, exception):
        self._throw_error(exception)

    def lock(self):
        self._cond.acquire()

    def unlock(self):
        self._cond.release()

    #########
    # state transitions
    #########

    def _sm_connect_poll(self):
        """
        Attempting to connect and setup the handshake
        """
        now = datetime.datetime.now()
        if now < self._next_connect_time:
            _g_logger.debug("Skipping reconnect until backoff time is "
                            "exceeded")
        else:
            _g_logger.debug("registering the connect event")
            parent_receive_q.register_user_callback(self._register_connect)

    def _sm_connect(self):
        try:
            self._ws = _WebSocketClient(
                self, self._server_url, self._receive_queue,
                protocols=['dcm'], heartbeat_freq=self._heartbeat_freq)
            self._ws.connect()
            self._ws.send_handshake(self._hs_string)
        except Exception as ex:
            _g_logger.exception("Failed to connect to %s" % self._server_url)
            self._throw_error(ex, notify=False)
            self._increase_backoff()

    def _sm_received_hs(self, incoming_handshake=None):
        """
        The handshake has arrived
        """
        try:
            self.handshake_doc = incoming_handshake
            self._errors_since_success = 0
            self._backoff_time = None
            rc = self.handshake_observer(incoming_handshake)
            if not rc:
                # this means the the AM rejected the handshake.  This is an
                # error and the connection returns to the waiting state
                ex = exceptions.AgentHandshakeException(incoming_handshake)
                self._throw_error(ex)
        except Exception as ex:
            self._throw_error(ex)

    def _sm_hs_failed(self):
        """
        An error occurred while waiting for the handshake
        """
        self._increase_backoff()

    def _sm_close_open(self):
        """
        A user called close while the connection was open
        """
        _g_logger.debug("close called when open")

        self._done_event.set()
        self._cond.notify()

    def _sm_hs_close(self):
        """
        A user called close while waiting for a handshake
        """
        _g_logger.debug("close event while handshaking")
        self._done_event.set()
        self._cond.notify()

    def _sm_not_open_close(self):
        """
        A user called close when the connection was not open
        """
        _g_logger.debug("close event while not open")
        self._done_event.set()
        self._cond.notify()

    def _sm_open_poll(self):
        """
        A poll event occurred in the open state.  Check the send queue
        """
        # check the send queue
        done = False
        while not done:
            try:
                doc = self._send_queue.get(False)
                self._send_queue.task_done()

                msg = json.dumps(doc)
                _g_logger.debug("sending the message " + msg)
                self._ws.send(msg)
                self._errors_since_success = 0
            except socket.error as er:
                if er.errno == errno.EPIPE:
                    _g_logger.info(
                        "The ws connection broke for %s" % self._server_url)
                else:
                    _g_logger.info(
                        "A WS socket error occurred %s" % self._server_url)
                self._throw_error(er)
                done = True
            except Queue.Empty:
                done = True
            except Exception as ex:
                _g_logger.exception(str(ex))
                self._throw_error(ex)
                done = True

    def _sm_open_error(self):
        """
        And error occured while the connection was open
        """
        self._increase_backoff()

    def _sm_waiting_error(self):
        """
        An error occurred while waiting on the connection.  This is an odd
        case
        """
        _g_logger.warn("An error occurred while waiting to try a new "
                       "connection.")

    def _sm_handshake_poll(self):
        """
        While waiting for the handshake a poll event occurred
        """
        pass

    def _sm_handshake_connect(self):
        """
        This could happen if the POLL event happened twice in the waiting
        state before the first one could try to connect.  Just ignore
        """
        pass

    def _setup_states(self):
        self._sm.add_transition(WsConnStates.WAITING,
                                WsConnEvents.POLL,
                                WsConnStates.WAITING,
                                self._sm_connect_poll)

        self._sm.add_transition(WsConnStates.WAITING,
                                WsConnEvents.ERROR,
                                WsConnStates.WAITING,
                                self._sm_waiting_error)

        self._sm.add_transition(WsConnStates.WAITING,
                                WsConnEvents.CONNECT_TIMEOUT,
                                WsConnStates.HANDSHAKING,
                                self._sm_connect)

        self._sm.add_transition(WsConnStates.WAITING,
                                WsConnEvents.CLOSE,
                                WsConnStates.DONE,
                                self._sm_not_open_close)

        self._sm.add_transition(WsConnStates.HANDSHAKING,
                                WsConnEvents.GOT_HANDSHAKE,
                                WsConnStates.OPEN,
                                self._sm_received_hs)

        self._sm.add_transition(WsConnStates.HANDSHAKING,
                                WsConnEvents.ERROR,
                                WsConnStates.WAITING,
                                self._sm_hs_failed)

        self._sm.add_transition(WsConnStates.HANDSHAKING,
                                WsConnEvents.POLL,
                                WsConnStates.HANDSHAKING,
                                self._sm_handshake_poll)

        self._sm.add_transition(WsConnStates.HANDSHAKING,
                                WsConnEvents.CONNECT_TIMEOUT,
                                WsConnStates.HANDSHAKING,
                                self._sm_handshake_connect)

        self._sm.add_transition(WsConnStates.HANDSHAKING,
                                WsConnEvents.CLOSE,
                                WsConnStates.DONE,
                                self._sm_hs_close)

        self._sm.add_transition(WsConnStates.OPEN,
                                WsConnEvents.CLOSE,
                                WsConnStates.DONE,
                                self._sm_close_open)

        self._sm.add_transition(WsConnStates.OPEN,
                                WsConnEvents.POLL,
                                WsConnStates.OPEN,
                                self._sm_open_poll)

        self._sm.add_transition(WsConnStates.OPEN,
                                WsConnEvents.ERROR,
                                WsConnStates.WAITING,
                                self._sm_open_error)

        self._sm.add_transition(WsConnStates.DONE,
                                WsConnEvents.POLL,
                                WsConnStates.DONE,
                                None)

        self._sm.add_transition(WsConnStates.DONE,
                                WsConnEvents.CONNECT_TIMEOUT,
                                WsConnStates.DONE,
                                None)

        self._sm.add_transition(WsConnStates.DONE,
                                WsConnEvents.ERROR,
                                WsConnStates.DONE,
                                None)
