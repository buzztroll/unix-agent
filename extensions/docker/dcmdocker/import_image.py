import json
import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class ImportImage(docker_utils.DockerJob):

    protocol_arguments = {
        "src": ("", True, str, None),
        "repository": ("", False, str, None),
        "tag": ("", False, str, None),
        "image": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ImportImage, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.import_image(
            src=self.args.src, repository=self.args.repository,
            tag=self.args.tag, image=self.args.image)
        out = json.loads(out)
        return plugin_base.PluginReply(
            0, reply_type="docker_import_image", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return ImportImage(conf, job_id, items_map, name, arguments)
