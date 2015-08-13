import dcm.agent.plugins.api.base as plugin_base


class RemoveUser(plugin_base.ScriptPlugin):

    protocol_arguments = {
        "userId":
        ("The unix account name of the user to remove",
         True, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RemoveUser, self).__init__(
            conf, job_id, items_map, name, arguments)
        self.ordered_param_list = [self.args.userId]


def load_plugin(conf, job_id, items_map, name, arguments):
    return RemoveUser(conf, job_id, items_map, name, arguments)
