import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class DeleteContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "v": ("", False, bool, False),
        "link": ("", False, bool, False),
        "force": ("", False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DeleteContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        self.docker_conn.remove_container(
            self.args.container, v=self.args.v,
            link=self.args.link, force=self.args.force)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return DeleteContainer(conf, job_id, items_map, name, arguments)
