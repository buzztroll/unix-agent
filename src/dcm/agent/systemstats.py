#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import psutil
import threading
import time

import dcm.agent.exceptions as exceptions
import dcm.agent.utils as agent_util


_g_logger = logging.getLogger(__name__)


class SystemStats(object):
    def __init__(self, name, hold_count, check_interval):
        self.interval = check_interval
        self.hold_count = hold_count
        self.name = name
        self._done = False
        self._stat_values = []
        self.cond = threading.Condition()
        self._t = threading.Thread(target=self.run)
        self._t.start()

    def run(self):
        try:
            while not self._done:
                self.poll()
        except Exception as ex:
            _g_logger.exception(
                "The system stat collector " + self.name + " failed with " +
                str(ex))

    # this should only be called from below wait(), and thus locked
    def add_value(self, v):
        self.cond.acquire()
        try:
            self._stat_values.append(v)
            if len(self._stat_values) > self.hold_count:
                self._stat_values = self._stat_values[-self.hold_count:]
        finally:
            self.cond.release()

    def poll(self):
        self.cond.acquire()
        try:
            self.cond.wait(self.interval)
        finally:
            self.cond.release()

    def stop(self):
        self.cond.acquire()
        try:
            self._done = True
            self.cond.notify()
        finally:
            self.cond.release()
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
        load = psutil.cpu_percent(self.interval) / 100.0
        timestamp = time.time()
        self.add_value({'timestamp': timestamp,
                        'cpu-idle': 1.0 - load})

    def get_stats_type(self):
        return "cpu_idle_stat_array"


class AgentVerboseSystemStats(SystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentVerboseSystemStats, self).__init__(
            name, hold_count, check_interval)

    def poll(self):
        load = psutil.cpu_percent(self.interval) / 100.0
        disk_io_info = psutil.disk_io_counters()
        net_io_info = psutil.net_io_counters()
        timestamp = time.time()
        self.add_value({'timestamp': timestamp,
                        'cpu-load': load,
                        'disk-read-ops': disk_io_info.read_count,
                        'disk-write-ops': disk_io_info.write_count,
                        'disk-read-bytes': disk_io_info.read_bytes,
                        'disk-write-bytes': disk_io_info.write_bytes,
                        'net-bytes-in': net_io_info.bytes_recv,
                        'net-bytes-out': net_io_info.bytes_sent})

    def get_stats_type(self):
        return "system_info_stat_array"


class AgentOverTimeSystemStats(SystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentOverTimeSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.previous_value = None
        self.type_name = None

    def _get_value(self, new_val):
        p_val = self.previous_value
        self.previous_value = new_val
        if p_val is None:
            return None
        val = (new_val - p_val) / self.interval
        timestamp = time.time()
        self.add_value({'timestamp': timestamp,
                        self.type_name: val})


class AgentDiskReadOpsSystemStats(AgentOverTimeSystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentDiskReadOpsSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.type_name = 'disk-read-ops'

    def poll(self):
        super(AgentDiskReadOpsSystemStats, self).poll()
        disk_io_info = psutil.disk_io_counters()
        val = self._get_value(disk_io_info.read_count)
        if val is None:
            return
        timestamp = time.time()
        self.add_value({'timestamp': timestamp,
                        'disk-read-ops': val})

    def get_stats_type(self):
        return "disk_read_ops_stat_array"


class AgentDiskWriteOpsSystemStats(AgentOverTimeSystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentDiskWriteOpsSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.type_name = 'disk-write-ops'

    def poll(self):
        super(AgentDiskWriteOpsSystemStats, self).poll()
        disk_io_info = psutil.disk_io_counters()
        self._get_value(disk_io_info.write_count)

    def get_stats_type(self):
        return "disk_write_ops_stat_array"


class AgentDiskReadByesSystemStats(AgentOverTimeSystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentDiskReadByesSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.type_name = 'disk-read-bytes'

    def poll(self):
        super(AgentDiskReadByesSystemStats, self).poll()
        disk_io_info = psutil.disk_io_counters()
        self._get_value(disk_io_info.read_bytes)

    def get_stats_type(self):
        return "disk_read_bytes_stat_array"


class AgentDiskWriteBytesSystemStats(AgentOverTimeSystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentDiskWriteBytesSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.type_name = 'disk-write-bytes'

    def poll(self):
        super(AgentDiskWriteBytesSystemStats, self).poll()
        disk_io_info = psutil.disk_io_counters()
        self._get_value(disk_io_info.write_bytes)

    def get_stats_type(self):
        return "disk_write_bytes_stat_array"


class AgentNetInByesSystemStats(AgentOverTimeSystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentNetInByesSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.type_name = 'net-bytes-in'

    def poll(self):
        super(AgentNetInByesSystemStats, self).poll()
        net_io_info = psutil.net_io_counters()
        self._get_value(net_io_info.bytes_recv)

    def get_stats_type(self):
        return "net_bytes_in_stat_array"


class AgentNetOutByesSystemStats(AgentOverTimeSystemStats):
    def __init__(self, name, hold_count, check_interval):
        super(AgentNetOutByesSystemStats, self).__init__(
            name, hold_count, check_interval)
        self.type_name = 'net-bytes-out'

    def poll(self):
        super(AgentNetOutByesSystemStats, self).poll()
        net_io_info = psutil.net_io_counters()
        self._get_value(net_io_info.bytes_sent)

    def get_stats_type(self):
        return "net_bytes_out_stat_array"


_g_stat_object_map = {
    "cpu-idle": CpuIdleSystemStats,
    "system-stats": AgentVerboseSystemStats,
    "disk-read-ops": AgentDiskReadOpsSystemStats,
    "disk-write-ops": AgentDiskWriteOpsSystemStats,
    "disk-read-bytes": AgentDiskReadByesSystemStats,
    "disk-write-bytes": AgentDiskWriteBytesSystemStats,
    "net-bytes-in": AgentNetInByesSystemStats,
    "net-bytes-out": AgentNetOutByesSystemStats
}


_g_active_stats = {}
_g_lock = threading.Lock()


def add_system_stat(stat_type, obj):
    _g_lock.acquire()
    try:
        _g_stat_object_map[stat_type] = obj
    finally:
        _g_lock.release()


def start_new_system_stat(
        name, stat_type, hold_count, check_interval, **kwvals):
    if stat_type not in _g_stat_object_map:
        raise exceptions.AgentOptionValueException(
            "stat_type", stat_type, str(list(_g_stat_object_map.keys())))

    _g_lock.acquire()
    try:
        if name in _g_active_stats:
            raise exceptions.AgentOptionValueAlreadySetException(name)

        cls = _g_stat_object_map[stat_type]
        stat_obj = cls(name, hold_count, check_interval, **kwvals)
        _g_active_stats[name] = stat_obj
    finally:
        _g_lock.release()


def get_stats(name):
    _g_lock.acquire()
    try:
        if name not in _g_active_stats:
            raise exceptions.AgentOptionValueNotSetException("name")
        stat_obj = _g_active_stats[name]
        return stat_obj.get_stats()
    finally:
        _g_lock.release()


def get_stats_type(name):
    _g_lock.acquire()
    try:
        if name not in _g_active_stats:
            raise exceptions.AgentOptionValueNotSetException("name")
        stat_obj = _g_active_stats[name]
        return stat_obj.get_stats_type()
    finally:
        _g_lock.release()


def stop_stats(name):
    _g_lock.acquire()
    try:
        if name not in _g_active_stats:
            raise exceptions.AgentOptionValueNotSetException("name")
        stat_obj = _g_active_stats[name]
        stat_obj.stop()
        del _g_active_stats[name]
    finally:
        _g_lock.release()


def clean_up_all():
    _g_lock.acquire()
    try:
        for name in list(_g_active_stats.keys()):
            stat_obj = _g_active_stats[name]
            stat_obj.stop()
            del _g_active_stats[name]
    finally:
        _g_lock.release()
