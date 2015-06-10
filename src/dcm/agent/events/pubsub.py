import logging
import threading


_g_logger = logging.getLogger(__name__)


def _deliver_topic(
        subs=None, topic_args=None, topic_kwargs=None, done_cb=None,
        done_kwargs=None):

    # set the topic error to the first callback to fail and then stop
    # calling them
    topic_error = None
    try:
        for s in subs:
            if topic_args is None:
                topic_args = []
            if topic_kwargs is None:
                topic_kwargs = {}
            s(*topic_args, **topic_kwargs)
    except BaseException as ex:
        topic_error = ex

    if done_cb is not None:
        if done_kwargs is None:
            done_kwargs = {}
        done_cb(topic_error, **done_kwargs)


class PubSubEvent(object):

    def __init__(self, event_space):
        self._event_space = event_space
        self._done = False
        self._subscribers = {}
        self._lock = threading.RLock()

    def publish(self,
                topic,
                topic_args=None,
                topic_kwargs=None, done_cb=None, done_kwargs=None):
        self._lock.acquire()
        try:
            try:
                subs = self._subscribers[topic][:]
            except KeyError:
                subs = []  # set this to empty to trip the done_cb

            ka = {'topic_args': topic_args,
                  'topic_kwargs': topic_kwargs,
                  'subs': subs,
                  'done_cb': done_cb,
                  'done_kwargs': done_kwargs}
            self._event_space.register_callback(_deliver_topic, kwargs=ka)
        finally:
            self._lock.release()

    def subscribe(self, topic, cb):
        self._lock.acquire()
        try:
            try:
                subs = self._subscribers[topic]
            except KeyError:
                subs = []
                self._subscribers[topic] = subs
            subs.append(cb)
        finally:
            self._lock.release()

    def unsubscribe(self, topic, cb):
        self._lock.acquire()
        try:
            try:
                subs = self._subscribers[topic]
            except KeyError:
                raise
            subs.remove(cb)
            if not subs:
                del self._subscribers[topic]
        finally:
            self._lock.release()
