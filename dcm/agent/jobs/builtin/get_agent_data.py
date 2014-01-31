import multiprocessing
import platform
import psutil
import dcm.agent.jobs as jobs


class GetAgentData(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetAgentData, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name),
                        arguments["serviceId"]]

    def call(self):
        (total_ram, used_ram, f, p) = psutil.phymem_usage()
        reply_object = {
            "cpu_count": multiprocessing.cpu_count(),
            "cpu_load": 0.0,
            "current_ram": used_ram,
            "max_ram": total_ram,
            "processes": len(psutil.get_process_list()),
            "platform": platform.platform(),
            # NOTE(buzztroll) I am not sure what to do with server state.  The
            # available options suggest error or contention.  I think if we get
            # to this point in system those values should all be invalid.
            # meaning we should have rejected a new command long ago.
            "server_state": "OK"

        }

        reply_doc = {
            "return_code": 0,
            "reply_type": "agent_data",
            "reply_object": reply_object
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetAgentData(conf, job_id, items_map, name, arguments)
