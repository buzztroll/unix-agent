import dcm.agent.plugins.api.base as plugin_base


class Terminate(plugin_base.ScriptPlugin):

    protocol_arguments = {
        "ignoreErrors":
        ("Ignore any errors that are returned from the terminate script",
         False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Terminate, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = [self.args.ignoreErrors]


def load_plugin(conf, job_id, items_map, name, arguments):
    return Terminate(conf, job_id, items_map, name, arguments)
