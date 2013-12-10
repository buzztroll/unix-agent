import logging
import os
import sys
import threading
import traceback
import uuid


def class_method_sync():
    def wrapper(func):
        def lock_func(self, *args, **kwargs):
            self.lock()
            try:
                return func(self, *args, **kwargs)
            finally:
                self.unlock()
        return lock_func
    return wrapper


def build_assertion_exception(logger, assertion_failure, msg):
    details_out = " === Stacktrace=== " + os.linesep
    for threadId, stack in sys._current_frames().items():
        details_out = details_out + os.linesep + \
            "##### Thread %s #####" % threadId + os.linesep
        for filename, lineno, name, line in traceback.extract_stack(stack):
            details_out = details_out + os.linesep + \
                'File: "%s", line %d, in %s' % (filename, lineno, name)
        if line:
            details_out = details_out + os.linesep + line.strip()

    msg = assertion_failure + " | " + msg + " | " + details_out
    logger.error(msg)

    #raise exceptions.AssertionFailure(msg)


def new_message_id():
    message_id = str(uuid.uuid4())
    return message_id


class MessageTimer(object):

    def __init__(self, timeout, callback, message_doc):
        self._send_doc = message_doc
        self._timeout = timeout
        self._cb = callback
        self.message_id = None
        self._timer = None

    def send(self, conn):
        if self._timer is not None:
            pass
        self._timer = threading.Timer(self._timeout,
                                      self._cb,
                                      args=[self])
        self.message_id = new_message_id()
        self._send_doc["message_id"] = self.message_id
        conn.send(self._send_doc)
        self._timer.start()

    def cancel(self):
        self._timer.cancel()
        self._timer = None


class AckCleanupTimer(object):
    def __init__(self, timeout, func):
        self._func = func
        self._timer = threading.Timer(timeout)

    def start(self):
        return self._timer.start()

    def cancel(self):
        return self._timer.cancel()

    def timeout_wrapper(self, *args, **kwargs):
        self._func(self, *args, **kwargs)
