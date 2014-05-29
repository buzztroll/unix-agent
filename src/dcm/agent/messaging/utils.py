import logging
import os
import sys
import threading
import traceback
import uuid


_g_logger = logging.getLogger(__name__)
_g_message_uuid = str(uuid.uuid4()).split("-")[0]
_g_message_id_count = 0


def class_method_sync(func):
    def wrapper(self, *args, **kwargs):
        self.lock()
        try:
            return func(self, *args, **kwargs)
        finally:
            self.unlock()
    return wrapper


def new_message_id():
    # note: using uuid here caused deadlock in tests
    global _g_message_id_count
    global _g_message_uuid
    # TODO lock this... maybe.  it doesnt really matter that much
    _g_message_id_count = _g_message_id_count + 1
    return _g_message_uuid + str(_g_message_id_count)


class MessageTimer(object):

    def __init__(self, timeout, callback, message_doc):
        self._send_doc = message_doc
        self._timeout = timeout
        self._cb = callback
        self._timer = None
        self._lock = threading.RLock()
        self.message_id = message_doc['message_id']

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    @class_method_sync
    def send(self, conn):
        _g_logger.info("Resending reply to %s" % self._send_doc["request_id"])
        self._timer = threading.Timer(self._timeout,
                                      self._cb,
                                      args=[self])
        self._send_doc['entity'] = "timer"
        conn.send(self._send_doc)
        self._timer.start()

    @class_method_sync
    def cancel(self):
        if self._timer is None:
            return
        self._timer.cancel()
        self._timer = None


class AckCleanupTimer(object):
    def __init__(self, timeout, func):
        self._func = func
        self._timer = threading.Timer(timeout, self.timeout_wrapper)

    def start(self):
        return self._timer.start()

    def cancel(self):
        return self._timer.cancel()

    def timeout_wrapper(self, *args, **kwargs):
        self._func(self, *args, **kwargs)
