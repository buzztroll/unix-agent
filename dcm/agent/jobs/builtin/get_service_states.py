import dcm.agent.utils as utils
import dcm.agent.jobs as jobs


class GetServiceStates(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetServiceStates, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name),
                        arguments["serviceId"]]

    def call(self):
        (stdout, stderr, rc) = utils.run_command(self.command)

def load_plugin(conf, job_id, items_map, name, arguments):
    return GetServiceStates(conf, job_id, items_map, name, arguments)
