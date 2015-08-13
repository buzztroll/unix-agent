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
