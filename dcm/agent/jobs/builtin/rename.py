import dcm.agent.jobs.builtin.direct_pass as direct_pass


class Rename(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Rename, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = ["serverName", "ipAddress"]


def load_plugin(conf, job_id, items_map, name, arguments):
    return Rename(conf, job_id, items_map, name, arguments)
