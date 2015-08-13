import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class TopContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(TopContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.top(self.args.container)
        return plugin_base.PluginReply(
            0, reply_object=out, reply_type="docker_top")


def load_plugin(conf, job_id, items_map, name, arguments):
    return TopContainer(conf, job_id, items_map, name, arguments)
