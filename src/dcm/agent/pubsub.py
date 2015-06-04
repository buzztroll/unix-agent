import logging
import threading


_g_logger = logging.getLogger(__name__)


class PubSubEvent(object):

    def __init__(self, event_space):
        self._event_space = event_space
        self._done = False
        self._subscribers = {}
        self._lock = threading.RLock()

    def publish(self, topic, *args, **kwargs):
        self._lock.acquire()
        try:
            try:
                subs = self._subscribers[topic]
            except KeyError:
                return
            for sub_cb in subs:
                self._event_space.register_callback(
                    sub_cb, args=args, kwargs=kwargs)
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
