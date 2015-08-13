import uuid

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.pages as pages

import dcmdocker.utils as docker_utils


class DockerListContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "quiet": ("", False, bool, False),
        "all": ("", False, bool, False),
        "trunc": ("", False, bool, True),
        "latest": ("", False, bool, False),
        "since": ("", False, str, None),
        "before": ("", False, str, None),
        "page_token": ("", False, str, None),
        "limit": ("", False, int, -1)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerListContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        if self.args.page_token is None:
            out = self.docker_conn.containers(quiet=self.args.quiet,
                                              all=self.args.all,
                                              trunc=self.args.trunc,
                                              latest=self.args.latest,
                                              since=self.args.since,
                                              before=self.args.before,
                                              limit=self.args.limit)
            token = str(uuid.uuid4()).replace("-", "")
            pager = pages.JsonPage(12*1024, out)
            self.conf.page_monitor.new_pager(pager, token)
        else:
            token = self.args.page_token

        page, token = self.conf.page_monitor.get_next_page(token)
        out = {'next_token': token, 'containers': page}
        return plugin_base.PluginReply(
            0, reply_type="docker_container_array", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return DockerListContainer(conf, job_id, items_map, name, arguments)
