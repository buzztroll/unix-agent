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

import datetime
import errno
import json
import logging
import Queue
import socket
import threading

import ws4py.client.threadedclient as ws4py_client

from dcm.agent import exceptions
import dcm.agent.connection.connection_interface as conn_iface


_g_logger = logging.getLogger(__name__)


class _WebSocketClient(ws4py_client.WebSocketClient):

    def __init__(self, manager, url, receive_queue, protocols=None,
                 extensions=None,
                 heartbeat_freq=None, ssl_options=None, headers=None):
        ws4py_client.WebSocketClient.__init__(
            self, url, protocols=protocols, extensions=extensions,
            heartbeat_freq=heartbeat_freq, ssl_options=ssl_options,
            headers=headers)
        self.receive_queue = receive_queue
        self.manager = manager
        self._url = url
        self._complete_handshake = False
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._handshake_reply = None

    def send_handshake(self, handshake):
        _g_logger.debug("Sending handshake")
        try:
            self._cond.acquire()
            self.send(handshake)
        except Exception as ex:
            _g_logger.error("An error occurred sending the handshake.")
        finally:
            self._cond.release()

    def wait_for_handshake(self):
        try:
            self._cond.acquire()
            while not self._complete_handshake:
                self._cond.wait()
        except Exception as ex:
            _g_logger.error("An error occurred waiting for the handshake to "
                            "complete.")
        finally:
            self._cond.release()
        return self._handshake_reply

    def opened(self):
        _g_logger.debug("Web socket %s has been opened" % self._url)

    def closed(self, code, reason=None):
        _g_logger.debug("Web socket %s has been closed %d %s"
                        % (self._url, code, reason))
        self.manager.closed(code, reason=reason)

    def received_message(self, m):
        if not self._complete_handshake:
            try:
                _g_logger.debug("WS message received " + m.data)
                self._cond.acquire()
                self._complete_handshake = True
                self._cond.notify_all()
                self._handshake_reply = m.data
            finally:
                self._cond.release()
        else:
            self.receive_queue.put(m.data)


class _WSManager(threading.Thread):

    def __init__(self, server_url, receive_queue, send_queue,
                 max_backoff=3, **kwargs):
        super(_WSManager, self).__init__()

        self._server_url = server_url
        self._receive_queue = receive_queue
        self._send_queue = send_queue
        self._kwargs = kwargs
        self._ws = None
        self._max_backoff = max_backoff
        self._connected = False
        self._reset_backoff()
        self._hs_string = None
        self._done = False

    def set_handshake(self, hs):
        self._hs_string = hs

    def _connect(self):
        tm = datetime.datetime.now()
        if tm < self._next_connection_time:
            return
        # TODO there should be a maximum wait for connect time that throws a
        # catastrophic error

        try:
            self._ws = _WebSocketClient(
                self, self._server_url, self._receive_queue, **self._kwargs)
            self._ws.connect()
            self._reply_hs_doc = self._ws.send_handshake(self._hs_string)
            self._ws.wait_for_handshake()
            self._reset_backoff()
            self._connected = True
        except Exception as ex:
            _g_logger.info("An error forming the WS connection to %s occurred"
                           ": %s" % (self._server_url, ex.message))
            self._set_next_connection_time()
            self._connected = False

    def connect(self):
        while not self._connected:
            self._connect()
        self.start()
        return json.loads(self._ws._handshake_reply)

    def _reset_backoff(self):
        self._backoff = 1
        self._next_connection_time = datetime.datetime.now()

    def _set_next_connection_time(self):
        self._backoff += 1
        if self._backoff > self._max_backoff:
            self._backoff = self._max_backoff

        self._next_connection_time = datetime.datetime.now() +\
                                     datetime.timedelta(seconds=self._backoff)

    def closed(self, code, reason=None):
        # we might want to rest the back off if code is success
        self._set_next_connection_time()
        self._connected = False

    def poll(self):
        # This will try and send items from the queue or it will try to connect
        # if it is not connected
        if not self._connected:
            self._connect()
            return False

        try:
            doc = self._send_queue.get(False, 2)
        except Queue.Empty:
            return True

        try:
            self._ws.send(json.dumps(doc))
            self._send_queue.task_done()
        except socket.error as er:
            if er.errno == errno.EPIPE:
                self._connected = False
            else:
                raise
            # XXX TODO we may need to trap other exceptions as well
        return False

    def run(self):
        while not self._done:
            self.poll()

    def close(self):
        self._done = True
        if self._connected:
            self._ws.close()


class WebSocketConnection(conn_iface.ConnectionInterface):

    def __init__(self, server_url, **kwargs):
        self._send_queue = Queue.Queue()
        self._recv_queue = Queue.Queue()
        self._hs_string = None

        self._ws_manager = _WSManager(
            server_url, self._recv_queue, self._send_queue, **kwargs)

    def set_handshake(self, handshake_doc):
        self._hs_string = json.dumps(handshake_doc)
        self._ws_manager.set_handshake(self._hs_string)

    def connect(self):
        return self._ws_manager.connect()

    def recv(self):
        try:
            m = self._recv_queue.get(False)
            self._recv_queue.task_done()
            return json.loads(m)
        except Queue.Empty:
            return None

    def send(self, doc):
        self._send_queue.put(doc)

    def close(self):
        self._ws_manager.close()