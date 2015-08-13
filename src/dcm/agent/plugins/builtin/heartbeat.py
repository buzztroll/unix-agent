import dcm.agent.plugins.api.base as plugin_base


class Heartbeat(plugin_base.Plugin):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Heartbeat, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        return plugin_base.PluginReply(
            0, reply_type="string", reply_object=self.conf.state)


def load_plugin(conf, job_id, items_map, name, arguments):
    return Heartbeat(conf, job_id, items_map, name, arguments)
