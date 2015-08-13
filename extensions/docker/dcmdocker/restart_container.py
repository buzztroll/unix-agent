import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class RestartContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "timeout": ("", False, int, 10),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RestartContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        self.docker_conn.restart(self.args.container,
                                 self.args.timeout)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return RestartContainer(conf, job_id, items_map, name, arguments)
