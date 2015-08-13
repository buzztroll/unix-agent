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

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.utils as plugin_utils
import dcm.agent.systemstats as systemstats


_g_logger = logging.getLogger(__name__)


class TesterCpuIdleSystemStats(systemstats.SystemStats):

    def __init__(self, name, hold_count, check_interval, stat_filename=None):
        self.source_file_name = "/tmp/cpustats.txt"
        if stat_filename is not None:
            self.source_file_name = stat_filename
        super(TesterCpuIdleSystemStats, self).__init__(
            name, hold_count, check_interval)

    def poll(self):
        self.cond.acquire()
        try:
            with open(self.source_file_name, "r") as fptr:
                line = fptr.readline()
                while line:
                    la = line.split(":")
                    self.add_value({'timestamp': float(la[0]),
                                    'cpu-idle': float(la[1])})
                    line = fptr.readline()
        except BaseException as ex:
            _g_logger.exception("The test stat failed: " + str(ex))
        finally:
            self.cond.release()
        super(TesterCpuIdleSystemStats, self).poll()

    def get_stats_type(self):
        return "cpu_idle_stat_array"


class TesterInitSystemStat(plugin_base.Plugin):

    protocol_arguments = {
        "statType": ("The type of stat metric to initialize.", True,
                     str, None),
        "statName": ("The name of the new stat collector.", True, str, None),
        "holdCount": ("The number of stats to retain.", True, int, None),
        "checkInterval": ("The number of seconds over which to collect this "
                          "metric", True, float, None),
        "kwargs": ("A JSON doc for stat collector specific parameters",
                   False, plugin_utils.json_param_type, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(TesterInitSystemStat, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        kwargs = self.args.kwargs
        if kwargs is None:
            kwargs = {}
        systemstats.start_new_system_stat(
            self.args.statName,
            self.args.statType,
            self.args.holdCount,
            self.args.checkInterval,
            **kwargs)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    systemstats.add_system_stat("cpu-idle", TesterCpuIdleSystemStats)
    return TesterInitSystemStat(conf, job_id, items_map, name, arguments)
