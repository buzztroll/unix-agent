import datetime
import heapq
import logging
import threading


_g_logger = logging.getLogger(__name__)


class UserCallback(object):

    def __init__(self, func, args, kwargs, delay):
        self._func = func
        self._canceled = False
        self._called = False
        self._args = args
        if args is None:
            self._args = []
        self._kwargs = kwargs
        if kwargs is None:
            self._kwargs = {}
        self._time_ready = datetime.datetime.now() +\
                           datetime.timedelta(seconds=delay)
        self._lock = threading.RLock()
        self._rc = None
        self._exception = None

    def get_time_ready(self):
        self._lock.acquire()
        try:
            return self._time_ready
        finally:
            self._lock.release()

    def __cmp__(self, other):
        return cmp(self._time_ready, other.get_time_ready())

    def call(self):
        try:
            _g_logger.debug("UserCallback calling %s" % self._func.__name__)
            self._lock.acquire()
            try:
                if self._canceled:
                    return
                self._called = True
            finally:
                self._lock.release()

            self._rc = self._func(*self._args, **self._kwargs)
        except Exception as ex:
            _g_logger.error("UserCallback function %(func_name)s threw "
                            "exception %(ex)s" %
                            {'func_name': self._func.__name__,
                             'ex': str(ex)})
            self._exception = ex
        finally:
            _g_logger.debug("UserCallback function %s returned successfully."
                            % self._func.__name__)

    def _cancel(self):
        """
        :returns a boolean saying if the call was canceled or not.

        If true is returned the call was not an will not be called.
        If false is returned the call already happened or will happen
        """
        self._lock.acquire()
        try:
            self._time_ready = datetime.datetime.now()
            self._canceled = True
            return not self._called
        finally:
            self._lock.release()

    def is_ready(self, tm=None):
        if tm is None:
            tm = datetime.datetime.now()
        self._lock.acquire()
        try:
            return self._time_ready <= tm
        finally:
            self._lock.release()

    def get_rc(self):
        self._lock.acquire()
        try:
            return self._rc
        finally:
            self._lock.release()

    def get_exception(self):
        self._lock.acquire()
        try:
            return self._exception
        finally:
            self._lock.release()

    def has_run(self):
        """
        :return: bool indicating if the callback has run yet

        There is a small window of time where this is true but the callback
        has not actually run yet.  A true value here means that it will
        inevitably run imminently
        """
        self._lock.acquire()
        try:
            return self._called
        finally:
            self._lock.release()


class EventSpace(object):

    def __init__(self):
        self._q = []
        self._cond = threading.Condition()
        self._done = False

    def register_callback(self, func, args=None, kwargs=None, delay=0):
        self._cond.acquire()
        try:
            ub = UserCallback(func, args, kwargs, delay)
            heapq.heappush(self._q, ub)
            self._cond.notify()
            return ub
        finally:
            self._cond.release()

    def stop(self):
        self._cond.acquire()
        try:
            self._done = True
            self._cond.notify()
        finally:
            self._cond.release()

    def cancel_callback(self, ub):
        self._cond.acquire()
        try:
            rc = ub._cancel()
            self._cond.notify()
            return rc
        finally:
            self._cond.release()

    def poll(self, timeblock=5.0):
        now = datetime.datetime.now()
        end_time = now + datetime.timedelta(seconds=timeblock)
        done = False
        while not done:
            self._cond.acquire()
            try:
                if self._done:
                    return
                ready_ub = None
                head_ub = heapq.nsmallest(1, self._q)
                if not head_ub:
                    sleep_time = end_time
                elif not head_ub[0].is_ready(tm=None):
                    sleep_time = min(end_time, head_ub[0].get_time_ready())
                else:
                    ready_ub = heapq.heappop(self._q)

                if ready_ub is None:
                    td = sleep_time - now
                    self._cond.wait(td.total_seconds())
            finally:
                self._cond.release()

            if ready_ub is not None:
                ready_ub.call()

            now = datetime.datetime.now()
            done = end_time < now



