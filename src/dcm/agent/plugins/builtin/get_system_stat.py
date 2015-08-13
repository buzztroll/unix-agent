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
        return plugin_base.PluginReply(
            0,
            reply_type=systemstats.get_stats_type(self.args.statName),
            reply_object=systemstats.get_stats(self.args.statName))


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetSystemStat(conf, job_id, items_map, name, arguments)
