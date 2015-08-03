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


class DeleteSystemStat(plugin_base.Plugin):

    protocol_arguments = {
        "statName": ("The name of the stat collector to query.",
                     True, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DeleteSystemStat, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        systemstats.stop_stats(self.args.statName)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return DeleteSystemStat(conf, job_id, items_map, name, arguments)
