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
import errno
import json
import logging
import queue
import socket
import ssl
import threading

import ws4py.client.threadedclient as ws4py_client

import dcm.agent.exceptions as exceptions
import dcm.agent.handshake as handshake
import dcm.agent.logger as dcm_logger
import dcm.agent.events.state_machine as state_machine
import dcm.agent.utils as agent_utils

from dcm.agent.events.globals import global_space as dcm_events

_g_logger = logging.getLogger(__name__)
_g_wire_logger = agent_utils.get_wire_logger()


class WsConnEvents:
    POLL = "POLL"
    CONNECTING_FINISHED = "CONNECTING_FINISHED"
    CONNECT_TIMEOUT = "CONNECT_TIMEOUT"
    INCOMING_MESSAGE = "INCOMING_MESSAGE"
    SUCCESSFUL_HANDSHAKE = "SUCCESSFUL_HANDSHAKE"
    ERROR = "ERROR"
    CLOSE = "CLOSE"


class WsConnStates:
    WAITING = "WAITING"
    CONNECTING = "CONNECTING"
    HANDSHAKING = "HANDSHAKING"
    HANDSHAKE_RECEIVED = "HANDSHAKE_RECEIVED"
    OPEN = "OPEN"
    DONE = "DONE"


class Backoff(object):

    def __init__(self, max_backoff_seconds,
                 initial_backoff_second=0.5,
                 idle_modifier=0.25):
        self._backoff_seconds = initial_backoff_second
        self._max_backoff = max_backoff_seconds
        if self._backoff_seconds > self._max_backoff:
            self._backoff_seconds = self._max_backoff
        self._idle_modifier = idle_modifier
        self._ready_time = datetime.datetime.now()
        self._last_activity = self._ready_time

    def activity(self):
        self._ready_time = datetime.datetime.now()
        self._last_activity = self._ready_time

    def _set_ready_time(self, backoff):
        if backoff > self._max_backoff:
            backoff = self._max_backoff
        self._backoff_seconds = backoff
        new_ready_time = datetime.datetime.now() +\
            datetime.timedelta(seconds=self._backoff_seconds)
        if new_ready_time > self._ready_time:
            self._ready_time = new_ready_time

    def error(self):
        self._set_ready_time(self._backoff_seconds*2.0)

    def closed(self):
        idle_time = datetime.datetime.now() - self._last_activity
        self._set_ready_time(idle_time.total_seconds() * self._idle_modifier)

    def ready(self):
        return self._ready_time < datetime.datetime.now()

    def force_backoff_time(self, backoff_seconds):
        self._ready_time = datetime.datetime.now() +\
            datetime.timedelta(seconds=backoff_seconds)

    def seconds_until_ready(self):
        d = self._ready_time - datetime.datetime.now()
        return max(0.0, d.total_seconds())


class RepeatQueue(object):

    def __init__(self, max_req_id=500):
        self._q = queue.Queue()
        self._lock = threading.RLock()
        self._message_id_set = set()
        self._request_id_count = {}
        self._max_req_id = max_req_id + 1

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
                    if self._request_id_count[request_id] >= self._max_req_id:
                        msg = "TOO MANY MESSAGES FOR %s!" % request_id
                        _g_logger.error(msg)
                        agent_utils.build_assertion_exception(_g_logger, msg)
                        if self._request_id_count[request_id] ==\
                                self._max_req_id:
                            dcm_logger.log_to_dcm_console_overloaded(msg=msg)
                        return
            except Exception as ex:
                _g_logger.warn("Exception checking if message is a retrans "
                               "%s" % str(ex))
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
                               "%s" % str(ex))
            return item
        finally:
            self._lock.release()

    def task_done(self):
        return self._q.task_done()


class _WebSocketClient(ws4py_client.WebSocketClient):

    def __init__(self, manager, url, receive_callback, protocols=None,
                 extensions=None,
                 heartbeat_freq=None, ssl_options=None, headers=None):
        ws4py_client.WebSocketClient.__init__(
            self, url, protocols=protocols, extensions=extensions,
            heartbeat_freq=heartbeat_freq, ssl_options=ssl_options,
            headers=headers)
        _g_logger.info("Attempting to connect to %s" % url)

        self._receive_callback = receive_callback
        self.manager = manager
        self._url = url
        self._dcm_closed_called = False

    def opened(self):
        _g_logger.debug("Web socket %s has been opened" % self._url)

    def closed(self, code, reason=None):
        _g_logger.info("Web socket %s has been closed %d %s"
                       % (self._url, code, reason))
        _g_logger.debug("Sending error event to connection manager.")
        self.manager.event_error(exception=Exception(
            "Connection unexpectedly closed: %d %s" % (code, reason)))

    def close(self, code=1000, reason=''):
        self._dcm_closed_called = True
        return ws4py_client.WebSocketClient.close(
            self, code=code, reason=reason)

    def received_message(self, m):
        _g_wire_logger.debug("INCOMING\n--------\n%s\n--------" % str(m.data))
        json_doc = json.loads(m.data.decode())
        self.manager.event_incoming_message(json_doc)

    def send(self, payload, binary=False):
        _g_wire_logger.debug("OUTGOING\n--------\n%s\n--------" % str(payload))
        super(_WebSocketClient, self).send(payload, binary=binary)


class WebSocketConnection(threading.Thread):

    def __init__(self, server_url,
                 backoff_amount=5000, max_backoff=300000,
                 heartbeat=None, allow_unknown_certs=False, ca_certs=None):
        super(WebSocketConnection, self).__init__()
        self._send_queue = RepeatQueue()
        self._ws_manager = None
        self._server_url = server_url
        self._cond = threading.Condition()
        self._done_event = threading.Event()

        self._connect_timer = None

        self._backoff = Backoff(float(max_backoff) / 1000.0,
                                float(backoff_amount) / 1000.0)

        self._sm = state_machine.StateMachine(
            WsConnStates.WAITING, logger=_g_logger)
        self._setup_states()
        self._handshake_manager = None
        self._heartbeat_freq = heartbeat
        if allow_unknown_certs:
            cert_reqs = ssl.CERT_NONE
        else:
            cert_reqs = ssl.CERT_REQUIRED
        self._ssl_options = {'cert_reqs': cert_reqs, 'ca_certs': ca_certs}
        self.pre_hs_message_queue = queue.Queue()

    @agent_utils.class_method_sync
    def set_backoff(self, backoff_seconds):
        self._backoff.force_backoff_time(backoff_seconds)

    @agent_utils.class_method_sync
    def connect(self, receive_callback, handshake_manager):
        self._receive_callback = receive_callback
        self._handshake_manager = handshake_manager
        self.start()

    def _register_connect(self):
        _g_logger.debug("Registering a connection to DCM")
        if self._connect_timer is not None:
            raise exceptions.AgentRuntimeException(
                "There is already a connection registered")
        self._connect_timer = dcm_events.register_callback(
            self.event_connect_timeout,
            delay=self._backoff.seconds_until_ready())

    @agent_utils.class_method_sync
    def event_connect_timeout(self):
        self._connect_timer = None
        self._sm.event_occurred(WsConnEvents.CONNECT_TIMEOUT)

    @agent_utils.class_method_sync
    def send(self, doc):
        _g_logger.debug("Adding a message to the send queue")
        self._send_queue.put(doc)
        self._cond.notify_all()

    @agent_utils.class_method_sync
    def close(self):
        _g_logger.debug("Websocket connection closed.")
        self.event_close()

    @agent_utils.class_method_sync
    def run(self):
        self._register_connect()
        while not self._done_event.is_set():
            try:
                self._sm.event_occurred(WsConnEvents.POLL)
                self._cond.wait()
            except Exception as ex:
                _g_logger.exception("The ws connection poller loop had "
                                    "an unexpected exception.")
                self._throw_error(ex)

    #########
    # incoming events
    #########
    @agent_utils.class_method_sync
    def event_close(self):
        self._backoff.closed()
        self._sm.event_occurred(WsConnEvents.CLOSE)

    @agent_utils.class_method_sync
    def event_incoming_message(self, incoming_data):
        self._sm.event_occurred(WsConnEvents.INCOMING_MESSAGE,
                                incoming_data=incoming_data)

    @agent_utils.class_method_sync
    def event_error(self, exception=None):
        self._sm.event_occurred(WsConnEvents.ERROR)
        _g_logger.error(
            "State machine received an exception %s" % str(exception))

    @agent_utils.class_method_sync
    def event_successful_handshake(self, hs):
        self._sm.event_occurred(WsConnEvents.SUCCESSFUL_HANDSHAKE)

    def _throw_error(self, exception, notify=True):
        _g_logger.warning("throwing error %s" % str(exception))
        dcm_events.register_callback(self.event_error,
                                     kwargs={"exception": exception})
        if notify:
            self._cond.notify()

    def throw_error(self, exception):
        self._throw_error(exception)

    def lock(self):
        self._cond.acquire()

    def unlock(self):
        self._cond.release()

    def _forming_connection_thread(self):
        try:
            self._ws.connect()
            self.lock()
            try:
                self._sm.event_occurred(WsConnEvents.CONNECTING_FINISHED)
            finally:
                self.unlock()
        except BaseException as ex:
            self.event_error(exception=ex)

    #########
    # state transitions
    #########

    def _sm_connect_poll(self):
        """
        Attempting to connect and setup the handshake
        """
        pass

    def _sm_connect(self):
        try:
            self._ws = _WebSocketClient(
                self, self._server_url, self._receive_callback,
                protocols=['dcm'], heartbeat_freq=self._heartbeat_freq,
                ssl_options=self._ssl_options)
            dcm_events.register_callback(
                self._forming_connection_thread, in_thread=True)
        except Exception as ex:
            _g_logger.exception("Failed to connect to %s" % self._server_url)
            self._throw_error(ex, notify=False)
            self._cond.notify()

    def _sm_start_handshake(self):
        try:
            hs_doc = self._handshake_manager.get_send_document()
            _g_logger.debug("Sending handshake")
            self._ws.send(json.dumps(hs_doc))
        except Exception as ex:
            _g_logger.exception("Failed to send handshake")
            self._throw_error(ex, notify=False)
            self._cond.notify()

    def _sm_close_while_connecting(self):
        try:
            self._ws.close()
        except Exception as ex:
            _g_logger.warn("Error closing the connection " + str(ex))
        self._done_event.set()
        self._cond.notify_all()

    def _sm_error_while_connecting(self):
        try:
            self._ws.close()
        except Exception as ex:
            _g_logger.warn("Error closing the connection " + str(ex))
        self._backoff.error()
        self._cond.notify_all()
        self._register_connect()

    def _sm_received_hs(self, incoming_data=None):
        """
        The handshake has arrived
        """
        try:
            # if the handshake is rejected an exception will be thrown
            hs = self._handshake_manager.incoming_document(incoming_data)
            _g_logger.debug("We received a handshake with reply code %d"
                            % hs.reply_type)
            if hs.reply_type != handshake.HandshakeIncomingReply.REPLY_CODE_SUCCESS:
                _g_logger.warn("The handshake was rejected.")
                if hs.reply_type == handshake.HandshakeIncomingReply.REPLY_CODE_FORCE_BACKOFF:
                    _g_logger.info("Backing off for %f seconds"
                                   % float(hs.force_backoff))
                    self._backoff.force_backoff_time(hs.force_backoff)
                self._ws.close()
                ex = exceptions.AgentHandshakeException(hs.reply_type)
                self._throw_error(ex)
            else:
                dcm_events.register_callback(self.event_successful_handshake,
                                             kwargs={"hs": hs})
            self._cond.notify()
        except Exception as ex:
            self._throw_error(ex)

    def _sm_pre_handshake_message(self, incoming_data=None):
        """
        This happens when a handshake has already been received and in the
        unlock window while waiting to process success/failure another messages
        comes in from DCM.  In this case we queue the message and process it
        it the handshake is determined to be successful.
        """
        _g_logger.debug(
            "New message received before the handshake was processed")
        self.pre_hs_message_queue.put(incoming_data)

    def _sm_successful_handshake(self):
        """
        This is the standard case when a handshake is successfully processed
        """
        _g_logger.debug("The handshake was successfully processed")
        while not self.pre_hs_message_queue.empty:
            incoming_data = self.pre_hs_message_queue.get()
            dcm_events.register_callback(
                self._receive_callback, args=[incoming_data])
        self._backoff.activity()

    def _sm_open_incoming_message(self, incoming_data=None):
        _g_logger.debug("New message received")
        dcm_events.register_callback(
            self._receive_callback, args=[incoming_data])
        self._backoff.activity()

    def _sm_hs_failed(self):
        """
        An error occurred while waiting for the handshake
        """
        _g_logger.debug("close called while handshaking")

        try:
            self._ws.close()
        except Exception:
            _g_logger.exception(
                "Got an error while closing in handshake state")
        self._backoff.error()
        self._cond.notify()
        self._register_connect()

    def _sm_close_open(self):
        """
        A user called close while the connection was open
        """
        _g_logger.debug("close called when open")

        self._done_event.set()
        self._cond.notify_all()
        self._ws.close()

    def _sm_hs_close(self):
        """
        A user called close while waiting for a handshake
        """
        _g_logger.debug("close event while handshaking")
        self._done_event.set()
        self._cond.notify_all()

    def _sm_not_open_close(self):
        """
        A user called close when the connection was not open
        """
        _g_logger.debug("close event while not open")
        self._done_event.set()
        self._cond.notify_all()

    def _sm_open_poll(self):
        """
        A poll event occurred in the open state.  Check the send queue
        """

        # TODO XXXX find a way to send the data not in a lock
        # check the send queue
        done = False
        while not done:
            try:
                doc = self._send_queue.get(False)
                self._send_queue.task_done()

                msg = json.dumps(doc)
                self._ws.send(msg)
            except socket.error as er:
                if er.errno == errno.EPIPE:
                    _g_logger.info(
                        "The ws connection broke for %s" % self._server_url)
                else:
                    _g_logger.info(
                        "A WS socket error occurred %s" % self._server_url)
                self._throw_error(er)
                done = True
            except queue.Empty:
                done = True
            except Exception as ex:
                _g_logger.exception(str(ex))
                self._throw_error(ex)
                done = True

    def _sm_open_error(self):
        """
        An error occurred while the connection was open
        """
        self._cond.notify()
        self._register_connect()

    def _sm_waiting_error(self):
        """
        An error occurred while waiting on the connection.  This is an odd
        case
        """
        _g_logger.warn("An error occurred while waiting to try a new "
                       "connection.")
        self._backoff.error()

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

    def _sm_connection_finished_right_after_error(self):
        """
        This case occurs if the connection is registered and finished but
        an error occurs that gets the lock before the connection can
        report in successfully.  In this case we should have a websocket
        to clean up
        :return:
        """
        try:
            self._ws.close()
        except Exception:
            _g_logger.exception(
                "Got an error while closing in handshake state")

    def _sm_connection_finished_right_after_done(self):
        """
        This case occurs if the connection is registered and finishes but
        a close is called that gets the lock before the connection can
        report in successfully.  In this case we should have a websocket
        to clean up
        :return:
        """
        try:
            self._ws.close()
        except Exception:
            _g_logger.exception(
                "Got an error while closing in handshake state")

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
                                WsConnStates.CONNECTING,
                                self._sm_connect)
        self._sm.add_transition(WsConnStates.WAITING,
                                WsConnEvents.CLOSE,
                                WsConnStates.DONE,
                                self._sm_not_open_close)
        self._sm.add_transition(WsConnStates.WAITING,
                                WsConnEvents.CONNECTING_FINISHED,
                                WsConnStates.WAITING,
                                self._sm_connection_finished_right_after_error)

        self._sm.add_transition(WsConnStates.CONNECTING,
                                WsConnEvents.CLOSE,
                                WsConnStates.DONE,
                                self._sm_close_while_connecting)
        self._sm.add_transition(WsConnStates.CONNECTING,
                                WsConnEvents.ERROR,
                                WsConnStates.WAITING,
                                self._sm_error_while_connecting)
        self._sm.add_transition(WsConnStates.CONNECTING,
                                WsConnEvents.CONNECTING_FINISHED,
                                WsConnStates.HANDSHAKING,
                                self._sm_start_handshake)
        self._sm.add_transition(WsConnStates.CONNECTING,
                                WsConnEvents.CONNECT_TIMEOUT,
                                WsConnStates.CONNECTING,
                                None)
        self._sm.add_transition(WsConnStates.CONNECTING,
                                WsConnEvents.POLL,
                                WsConnStates.CONNECTING,
                                None)

        self._sm.add_transition(WsConnStates.HANDSHAKING,
                                WsConnEvents.INCOMING_MESSAGE,
                                WsConnStates.HANDSHAKE_RECEIVED,
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

        self._sm.add_transition(WsConnStates.HANDSHAKE_RECEIVED,
                                WsConnEvents.INCOMING_MESSAGE,
                                WsConnStates.HANDSHAKE_RECEIVED,
                                self._sm_pre_handshake_message)
        self._sm.add_transition(WsConnStates.HANDSHAKE_RECEIVED,
                                WsConnEvents.SUCCESSFUL_HANDSHAKE,
                                WsConnStates.OPEN,
                                self._sm_successful_handshake)
        self._sm.add_transition(WsConnStates.HANDSHAKE_RECEIVED,
                                WsConnEvents.ERROR,
                                WsConnStates.WAITING,
                                self._sm_hs_failed)
        self._sm.add_transition(WsConnStates.HANDSHAKE_RECEIVED,
                                WsConnEvents.POLL,
                                WsConnStates.HANDSHAKE_RECEIVED,
                                self._sm_handshake_poll)
        self._sm.add_transition(WsConnStates.HANDSHAKE_RECEIVED,
                                WsConnEvents.CONNECT_TIMEOUT,
                                WsConnStates.HANDSHAKE_RECEIVED,
                                self._sm_handshake_connect)
        self._sm.add_transition(WsConnStates.HANDSHAKE_RECEIVED,
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
                                WsConnEvents.INCOMING_MESSAGE,
                                WsConnStates.OPEN,
                                self._sm_open_incoming_message)
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
        self._sm.add_transition(WsConnStates.DONE,
                                WsConnEvents.INCOMING_MESSAGE,
                                WsConnStates.DONE,
                                None)
        # This can happen if close is called by the agent after the handshake
        # has been determine to be successful but before the the event comes in
        self._sm.add_transition(WsConnStates.DONE,
                                WsConnEvents.SUCCESSFUL_HANDSHAKE,
                                WsConnStates.DONE,
                                None)
        self._sm.add_transition(WsConnStates.DONE,
                                WsConnEvents.CONNECTING_FINISHED,
                                WsConnStates.DONE,
                                self._sm_connection_finished_right_after_done)
