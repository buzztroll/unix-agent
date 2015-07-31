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

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.systemstats as systemstats

_g_logger = logging.getLogger(__name__)


class GetSystemStat(plugin_base.Plugin):

    protocol_arguments = {
        "statName": ("The name of the stat collector to query.",
                     True, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetSystemStat, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        reply_doc = {
            "return_code": 0,
            "reply_type": systemstats.get_stats_type(self.args.statName),
            "reply_object": systemstats.get_stats(self.args.statName)
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetSystemStat(conf, job_id, items_map, name, arguments)
