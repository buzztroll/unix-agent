import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class DeleteImages(docker_utils.DockerJob):

    protocol_arguments = {
        "name": ("", True, str, None),
        "force": ("", False, bool, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DeleteImages, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        self.docker_conn.remove_image(self.args.name)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return DeleteImages(conf, job_id, items_map, name, arguments)
