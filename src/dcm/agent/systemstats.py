import threading
import psutil
import time

from dcm.agent import exceptions
import dcm.agent.utils as agent_util


class SystemStats(object):
    def __init__(self, name, hold_count, check_interval):
        self.interval = check_interval
        self.hold_count = hold_count
        self.name = name
        self._done = False
        self._stat_values = []
        self._cond = threading.Condition()
        self._t = threading.Thread(target=self.run)
        self._t.start()

    def run(self):
        while not self._done:
            self.poll()

    # this should only be called from below wait(), and thus locked
    def add_value(self, v):
        self._cond.acquire()
        try:
            self._stat_values.append(v)
            if len(self._stat_values) > self.hold_count:
                self._stat_values = self._stat_values[-self.hold_count:]
        finally:
            self._cond.release()

    def poll(self):
        self._cond.acquire()
        try:
            self._cond.wait(self.interval)
        finally:
            self._cond.release()

    def stop(self):
        self._cond.acquire()
        try:
            self._done = True
            self._cond.notify()
        finally:
            self._cond.release()
        self._t.join()

    def get_stats(self):
        return {'status': self._stat_values[:]}

    @agent_util.not_implemented_decorator
    def get_stats_type(self):
        pass


class CpuIdleSystemStats(SystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(CpuIdleSystemStats, self).__init__(
            name, hold_count, check_interval)

    def poll(self):
        load = psutil.cpu_percent(self.interval)
        timestamp = time.time()
        self.add_value({'timestamp': timestamp,
                        'cpu-idle': 1.0 - load})

    def get_stats_type(self):
        return "cpu_idle_stat_array"


_g_stat_object_map = {
    "cpu-idle": CpuIdleSystemStats
}


_g_active_stats = {}
_g_lock = threading.Lock()


def start_new_system_stat(name, stat_type, hold_count, check_interval):
    if stat_type not in _g_stat_object_map:
        raise exceptions.AgentOptionValueException(
            "stat_type", stat_type, str(_g_stat_object_map.keys()))

    _g_lock.acquire()
    try:
        if name in _g_active_stats:
            raise exceptions.AgentOptionValueAlreadySetException(name)

        cls = _g_stat_object_map[stat_type]
        stat_obj = cls(name, hold_count, check_interval)
        _g_active_stats[name] = stat_obj
    finally:
        _g_lock.release()


def get_stats(name):
    _g_lock.acquire()
    try:
        if name not in _g_active_stats:
            raise exceptions.AgentOptionValueNotSetException("name", name)
        stat_obj = _g_active_stats[name]
        return stat_obj.get_stats()
    finally:
        _g_lock.release()


def get_stats_type(name):
    _g_lock.acquire()
    try:
        if name not in _g_active_stats:
            raise exceptions.AgentOptionValueNotSetException("name", name)
        stat_obj = _g_active_stats[name]
        return stat_obj.get_stats_type()
    finally:
        _g_lock.release()


def stop_stats(name):
    _g_lock.acquire()
    try:
        if name not in _g_active_stats:
            raise exceptions.AgentOptionValueNotSetException("name", name)
        stat_obj = _g_active_stats[name]
        stat_obj.stop()
        del _g_active_stats[name]
    finally:
        _g_lock.release()


def clean_up_all():
    _g_lock.acquire()
    try:
        for name in _g_active_stats:
            stat_obj = _g_active_stats[name]
            stat_obj.stop()
            del _g_active_stats[name]
    finally:
        _g_lock.release()
