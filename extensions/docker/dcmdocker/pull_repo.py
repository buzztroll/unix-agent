import json
import logging

import dcm.agent.logger as dcm_logger
import dcm.agent.plugins.api.base as plugin_base

import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class PullRepo(docker_utils.DockerJob):

    protocol_arguments = {
        "repository": ("", True, str, None),
        "tag": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(PullRepo, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.pull(
            self.args.repository, tag=self.args.tag, stream=True)

        # only log the last line at info level
        id_map = {}
        for line in out:
            _g_logger.debug(line)
            try:
                j_obj = json.loads(line)
                id_map[j_obj['id']] = line
            except Exception as ex:
                _g_logger.debug("Error dealing with the pull output " + str(ex))
        for k in id_map:
            dcm_logger.log_to_dcm_console_job_details(
                job_name=self.name, details="pulled " + id_map[k])
        return plugin_base.PluginReply(
            0, reply_type="docker_pull", reply_object=None)


def load_plugin(conf, job_id, items_map, name, arguments):
    return PullRepo(conf, job_id, items_map, name, arguments)
