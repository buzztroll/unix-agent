import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class GetContainerDetails(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetContainerDetails, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.inspect_container(self.args.container)
        return plugin_base.PluginReply(
            0, reply_type="docker_inspect_container", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetContainerDetails(conf, job_id, items_map, name, arguments)
