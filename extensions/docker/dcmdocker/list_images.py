import logging
import uuid

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.pages as pages

import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class ListImages(docker_utils.DockerJob):

    protocol_arguments = {
        "name": ("", False, str, None),
        "page_token": ("", False, str, None),
        "quiet": ("", False, bool, False),
        "all": ("", False, bool, False),
        "viz": ("", False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ListImages, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._message_size_limit = 14 * 1024

    def run(self):
        if self.args.page_token is None:
            out = self.docker_conn.images(name=self.args.name,
                                          quiet=self.args.quiet,
                                          all=self.args.all,
                                          viz=self.args.viz)
            token = str(uuid.uuid4()).replace("-", "")
            pager = pages.JsonPage(12*1024, out)
            self.conf.page_monitor.new_pager(pager, token)
        else:
            token = self.args.page_token

        page, token = self.conf.page_monitor.get_next_page(token)
        out = {'next_token': token, 'images': page}
        return plugin_base.PluginReply(
            0, reply_type="docker_image_array", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return ListImages(conf, job_id, items_map, name, arguments)
