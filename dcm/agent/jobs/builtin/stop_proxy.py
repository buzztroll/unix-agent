import dcm.agent.jobs.builtin.direct_pass as direct_pass


class StopProxy(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StopProxy, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = ["toAddress"]


def load_plugin(conf, job_id, items_map, name, arguments):
    return StopProxy(conf, job_id, items_map, name, arguments)
