#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import logging

from dcm.agent import utils
import dcm.agent.jobs as jobs
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
        try:
            with open(self.source_file_name, "r") as fptr:
                line = fptr.readline()
                while line:
                    la = line.split(":")
                    self.add_value({'timestamp': float(la[0]),
                                    'cpu-idle': float(la[1])})
                    line = fptr.readline()
        except BaseException as ex:
            _g_logger.exception("The test stat failed: " + ex.message)
        super(TesterCpuIdleSystemStats, self).poll()

    def get_stats_type(self):
        return "cpu_idle_stat_array"


class TesterInitSystemStat(jobs.Plugin):

    protocol_arguments = {
        "statType": ("The type of stat metric to initialize.", True,
                     str, None),
        "statName": ("The name of the new stat collector.", True, str, None),
        "holdCount": ("The number of stats to retain.", True, int, None),
        "checkInterval": ("The number of seconds over which to collect this "
                          "metric", True, float, None),
        "kwargs": ("A JSON doc for stat collector specific parameters",
                   False, utils.json_param_type, None),
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
        reply_doc = {
            "return_code": 0,
            "reply_type": "void"
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    systemstats.add_system_stat("cpu-idle", TesterCpuIdleSystemStats)
    return TesterInitSystemStat(conf, job_id, items_map, name, arguments)
