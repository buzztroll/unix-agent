import datetime
import heapq
import logging
import threading


_g_logger = logging.getLogger(__name__)


class UserCallback(object):
    """
    This object is a handle to an event which was registered in an EventSpace.
    It can be used to cancel a registered event, check the event's status, or
    examine the results of a event that has completed.
    """

    def __init__(self, func, args, kwargs, delay, in_thread):
        self._func = func
        self._canceled = False
        self._called = False
        self._args = args
        self._in_thread = in_thread
        self._run_thread = None
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
        """
        :return: The time at which this callback will be ready to be called.
        """
        self._lock.acquire()
        try:
            return self._time_ready
        finally:
            self._lock.release()

    def __repr__(self):
        return str(self._func)

    def __lt__(self, other):
        return self._time_ready < other.get_time_ready()

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
        """
        :param tm: The time to check the ready time against.  If None the
        current time will be used.
        :return:  A bool indicating if this callback object is ready to be
        called.  If the associated delay has expired the callback is ready
        to be called and True is returned.
        """
        if tm is None:
            tm = datetime.datetime.now()
        self._lock.acquire()
        try:
            return self._time_ready <= tm
        finally:
            self._lock.release()

    def in_thread(self):
        return self._in_thread

    def get_rc(self):
        """
        Get the return value from the called function.  IF this is called
        before the callback is called it will return None in all cases
        :return: The return code from the function or None
        """
        self._lock.acquire()
        try:
            return self._rc
        finally:
            self._lock.release()

    def get_exception(self):
        """
        If when called the callback threw an exception a call to this method
        will retrieve that exception.  If no exception was called, or the
        callback has not yet been called this will be None
        :return: The exception returned from the callback
        """
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

    def join(self):
        """
        When a callback is run in its own thread the user may want to join
        that thread.  This method allows for this.
        """
        if self._run_thread:
            self._run_thread.join()
            self._run_thread = None


class EventSpace(object):
    """
    A class for managing and running events.

    This class allows a user to register events to be called either at a later
    time from a new thread or from the top level polling function.  This allows
    a functions to be scheduled for later execution outside of the registering
    functions call stack.  The events are managed by this object.  In some
    cases they can be canceled.  poll() must be called on this function in
    order for the events to occur.   The object is thread safe.  poll() can
    be called in a thread and the registered event callbacks are called
    unlocked and thus they can safely manipulate the event space which is
    managing them.
    """

    def __init__(self):
        """
        :return:
        """
        self._q = []
        self._cond = threading.Condition()
        self._done = False
        self._running_threads = []
        self._done_threads = []

    def register_callback(self, func, args=None, kwargs=None, delay=0,
                          in_thread=False):
        """
        :param func: The callable object (typically a function or a method)
         which will be called later by the event system.
        :param args: The list of arguments that will be passed to the callable
        func object as *args
        :param kwargs:
        The dictionary of arguments will be passed to the callable func object
        as **kwargs
        :param delay: The number or seconds to wait before calling func.  More
         time may expire but at least the given number of seconds will pass.
        :param in_thread: Run the callback in its own thread.
        :return: A UserCallback object which is a handle to this callback
        registration.  It can be used to inspect and manage that event.
        """
        self._cond.acquire()
        try:
            if self._done:
                raise Exception("We cannot register callbacks because this "
                                "space has been stopped.")
            ub = UserCallback(func, args, kwargs, delay, in_thread)
            heapq.heappush(self._q, ub)
            self._cond.notify()
            return ub
        finally:
            self._cond.release()

    def stop(self):
        """
        Stop this event space.  Once this is called no future events can be
        registered and this cannot be reused.  Outstanding events will be
        abandoned.
        :return: None
        """
        self._cond.acquire()
        try:
            self._done = True
            self._cond.notify()
        finally:
            self._cond.release()

    def cancel_callback(self, ub):
        """
        This will attempt to safely cancel a callback.  In some cases the
        callback will be too far into the registration process to successfully
        cancel, or it may have already been run.  If the cancel is successful
        True will be returned, otherwise False.
        :param ub:  The handle to the registered func to cancel.
        :return: A boolean indicating if the event was successfully canceled.
        """
        self._cond.acquire()
        try:
            rc = ub._cancel()
            self._cond.notify()
            return rc
        finally:
            self._cond.release()

    def _run_threaded(self, ub):
        this_thread = threading.currentThread()
        try:
            ub.call()
        finally:
            self._cond.acquire()
            try:
                self._running_threads.remove(this_thread)
                self._done_threads.append(this_thread)
                self._cond.notifyAll()
            finally:
                self._cond.release()

    def _build_ready_list(self, now, end_time):
        # get everything that is ready right now while under lock.  It nothing
        # is ready a time to sleep is returned
        ready_list = []
        done = False
        first_not_ready = None
        while not done:
            head_ub = heapq.nsmallest(1, self._q)
            if head_ub:
                if head_ub[0].is_ready(tm=now):
                    ub = heapq.heappop(self._q)
                    if ub.in_thread():
                        _run_thread = threading.Thread(
                            target=self._run_threaded,
                            args=(ub,))
                        self._running_threads.append(_run_thread)
                        _run_thread.start()
                    else:
                        ready_list.append(ub)
                else:
                    first_not_ready = head_ub[0]
                    done = True
            else:
                done = True
        if ready_list:
            sleep_time = 0.0
        else:
            if first_not_ready:
                ready_time = min(end_time, head_ub[0].get_time_ready())
            else:
                ready_time = end_time
            td = ready_time - now
            sleep_time = max(0.0, td.total_seconds())

        return ready_list, sleep_time

    def _clear_done_threads(self):
        # This should only be called locked
        for t in self._done_threads[:]:
            t.join()
            self._done_threads.remove(t)

    def poll(self, timeblock=5.0):
        """
        Poll an event space to check for ready event callbacks.  If a event
        is scheduled it will be called directly from the current call stack
        (if this object was initialized with use_threads=False) or it will
        be registered in a new thread.
        :param timeblock: The amount of time to wait for events to be ready
        :return: A boolean is returned to indicate if an event was called
        or not
        """
        now = datetime.datetime.now()
        end_time = now + datetime.timedelta(seconds=timeblock)
        done = False
        any_called = False
        while not done:
            self._cond.acquire()
            try:
                # if this event space was shutdown exit out immediately
                if self._done:
                    return any_called

                self._clear_done_threads()
                ready_to_unlock = False
                while not ready_to_unlock and not done:
                    ready_list, sleep_time =\
                        self._build_ready_list(now, end_time)
                    if not ready_list:
                        self._cond.wait(sleep_time)
                        # it is possible for the lock to wake up before the
                        # blocking time.  In this case we should see if any
                        # new callbacks are ready.
                    else:
                        # We have something to call so we need to unlock
                        ready_to_unlock = True

                    # check to see if time expired here to end all loops
                    now = datetime.datetime.now()
                    done = end_time < now
            finally:
                self._cond.release()

            # call everything that was found ready.  We may want to kick
            # these out in threads in the event that they block
            for ready_ub in ready_list:
                any_called = True
                ready_ub.call()
        return any_called

    def wakeup(self, cancel_all=False):
        """
        Wake up a call to poll even if no callbacks are ready
        :param cancel_all: If this is set all registered callbacks will be
        cancelled.
        :return:
        """
        self._cond.acquire()
        try:
            if cancel_all:
                for ub in self._q:
                    ub._cancel()
            self._cond.notifyAll()
        finally:
            self._cond.release()

    def reset(self):

        # first disallow any new registrations and cancel anything that has
        # not yet started
        self._cond.acquire()
        try:
            self._done = True
            # canceling everything in the list will mark everything that is
            # not already effectively running to never run
            for ub in self._q:
                ub._cancel()
            self._q = []
            while len(self._running_threads) > 0:
                self._cond.wait()
            self._clear_done_threads()
            # now that everything is clear allow new registrations again
            self._done = False
        finally:
            self._cond.release()


global_space = EventSpace()
