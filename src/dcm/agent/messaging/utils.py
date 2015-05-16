import logging
import threading
import uuid

import dcm.agent.utils as agent_utils


from dcm.agent.events import global_space as dcm_events


_g_logger = logging.getLogger(__name__)
_g_message_uuid = str(uuid.uuid4()).split("-")[0]
_g_message_id_count = 0
_g_guid_lock = threading.RLock()


def new_message_id():
    # note: using uuid here caused deadlock in tests
    global _g_message_id_count
    global _g_message_uuid
    _g_guid_lock.acquire()
    try:
        _g_message_id_count = _g_message_id_count + 1
    finally:
        _g_guid_lock.release()
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

    @agent_utils.class_method_sync
    def send(self, conn):
        _g_logger.info("Resending reply to %s" % self._send_doc["request_id"])
        self._send_doc['entity'] = "timer"
        conn.send(self._send_doc)
        self._timer = dcm_events.register_callback(self._cb, args=[self], delay=self._timeout)

    @agent_utils.class_method_sync
    def cancel(self):
        if self._timer is None:
            return
        dcm_events.cancel(self._timer)
        self._timer = None


class AckCleanupTimer(object):
    def __init__(self, timeout, func):
        self._func = func
        self._timeout = timeout

    def start(self):
        self._timer = dcm_events.register_callback(
            self.timeout_wrapper, delay=self._timeout)

    def cancel(self):
        return dcm_events.cancel(self._timer)

    def timeout_wrapper(self, *args, **kwargs):
        self._func(self, *args, **kwargs)
