import Queue
import logging
import threading

import dcm.agent.utils as agent_util


_g_logger = logging.getLogger(__name__)


class UserCallback(object):

    def __init__(self, func, args, kwargs):
        self._func = func
        self._args = args
        if args is None:
            self._args = []
        self._kwargs = kwargs
        if kwargs is None:
            self._kwargs = {}

    def call(self):
        try:
            _g_logger.debug("UserCallback calling %s" % self._func.__name__)
            self._func(*self._args, **self._kwargs)
        except Exception as ex:
            _g_logger.error("UserCallback function %(func_name)s threw "
                            "exception %(ex)s" %
                            {'func_name': self._func.__name__,
                             'ex': str(ex)})
            raise
        finally:
            _g_logger.debug("UserCallback function %s returned successfully."
                            % self._func.__name__)


class ParentReceiveQObserver(object):
    @agent_util.not_implemented_decorator
    def incoming_parent_q_message(self, obj):
        pass


class CBCallerFromQ(ParentReceiveQObserver):
    def incoming_parent_q_message(self, cb):
        cb.call()


class _PutTargetQueue(object):
    def __init__(self, name, main_q):
        self._name = name
        self._main_q = main_q

    def put(self, msg_obj):
        self._main_q.add_message(self._name, msg_obj)


class _MainQueue(ParentReceiveQObserver):

    def __init__(self):
        self._q = Queue.Queue()
        self._targets = {}
        self._shutdown_msg_type = "SHUTDOWN_MSG_TYPE"
        self._lock = threading.RLock()
        self.add_target(self._shutdown_msg_type, self)

        self._callback_manager = CBCallerFromQ()
        self._user_callbacks_queue = self.get_put_queue(
            self._callback_manager, str(self._callback_manager))

    def register_put_queue(self, put_q, handler_obj):
        self.add_target(put_q.name, handler_obj)

    def get_put_queue(self, handler_obj, name):
        put_q = _PutTargetQueue(name, self)
        self.add_target(name, handler_obj)
        return put_q

    def remove_target(self, msg_type):
        with self._lock:
            if msg_type not in self._targets:
                raise Exception("That target is not in use.")
            del self._targets[msg_type]

    def add_target(self, msg_type, target_object, safe=True):
        with self._lock:
            if safe and msg_type in self._targets:
                raise Exception("That target is already in use. %s" % msg_type)
            self._targets[msg_type] = target_object

    def add_message(self, msg_type, msg_obj):
        with self._lock:
            if msg_type not in self._targets:
                _g_logger.error(
                    "This is not a valid message type: %s" % msg_type)
                return
            self._q.put((msg_type, msg_obj))

    def poll(self, blocking=True, timeblock=5):
        try:
            (msg_type, msg_obj) = self._q.get(blocking, timeblock)
        except Queue.Empty:
            return False
        with self._lock:
            try:
                if msg_type not in self._targets:
                    _g_logger.error(
                        "This is not a valid message type: %s" % msg_type)
                    return
                handler = self._targets[msg_type]
            finally:
                self._q.task_done()
        handler.incoming_parent_q_message(msg_obj)
        return True

    def flush(self):
        rc = True
        while rc:
            rc = self.poll(False, 0)

    def shutdown(self):
        with self._lock:
            self._q.put((self._shutdown_msg_type, self))

    def incoming_parent_q_message(self, msg_object):
        # this is just to wake up the lock
        pass

    def register_user_callback(self, func, args=None, kwargs=None):
        cb = UserCallback(func, args, kwargs)
        self._user_callbacks_queue.put(cb)


_g_main_q_maker = _MainQueue()


def get_master_receive_queue(handler, name):
    return _g_main_q_maker.get_put_queue(handler, name)


def register_user_callback(func, args=None, kwargs=None):
    return _g_main_q_maker.register_user_callback(func, args, kwargs)


def poll(blocking=True, timeblock=5):
    _g_main_q_maker.poll(blocking=blocking, timeblock=timeblock)


def create_put_q(name):
    return _PutTargetQueue(name, _g_main_q_maker)


def register_put_queue(put_q, handler_obj):
    _g_main_q_maker.add_target(put_q._name, handler_obj)


def set_put_queue(put_q, handler_obj):
    _g_main_q_maker.add_target(put_q._name, handler_obj, safe=False)


def unregister_put_queue(put_q):
    _g_main_q_maker.remove_target(put_q._name)


def wakeup():
    _g_main_q_maker.shutdown()


def flush():
    _g_main_q_maker.flush()
