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

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.systemstats as systemstats


class InitSystemStat(plugin_base.Plugin):

    protocol_arguments = {
        "statType": ("The type of stat metric to initialize.", True,
                     str, None),
        "statName": ("The name of the new stat collector.", True, str, None),
        "holdCount": ("The number of stats to retain.", True, int, None),
        "checkInterval": ("The number of seconds over which to collect this "
                          "metric", True, float, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InitSystemStat, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        systemstats.start_new_system_stat(
            self.args.statName,
            self.args.statType,
            self.args.holdCount,
            self.args.checkInterval)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return InitSystemStat(conf, job_id, items_map, name, arguments)
