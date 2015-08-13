import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class IsDockerHost(docker_utils.DockerJob):

    protocol_arguments = {
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(IsDockerHost, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        return plugin_base.PluginReply(
            0, reply_type="boolean", reply_object=True)


def load_plugin(conf, job_id, items_map, name, arguments):
    return IsDockerHost(conf, job_id, items_map, name, arguments)
