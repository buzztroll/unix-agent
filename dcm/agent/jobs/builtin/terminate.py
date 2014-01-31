import dcm.agent.jobs.builtin.direct_pass as direct_pass


class Terminate(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Terminate, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = ["ignoreErrors"]


def load_plugin(conf, job_id, items_map, name, arguments):
    return Terminate(conf, job_id, items_map, name, arguments)
