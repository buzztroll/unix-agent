import dcm.agent.jobs.builtin.direct_pass as direct_pass


class RemoveUser(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RemoveUser, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = ["user_id"]


def load_plugin(conf, job_id, items_map, name, arguments):
    return RemoveUser(conf, job_id, items_map, name, arguments)
