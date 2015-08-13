import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class StopContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "timeout": ("", False, int, 10),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StopContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        self.docker_conn.stop(self.args.container,
                              timeout=self.args.timeout)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return StopContainer(conf, job_id, items_map, name, arguments)
