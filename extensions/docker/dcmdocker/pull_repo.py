#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
            line = line.decode()
            j_obj = json.loads(line)
            if 'id' in j_obj:
                id_map[j_obj['id']] = line
            elif 'error' in j_obj:
                _g_logger.error(
                    "Error pulling the image " + line)
                raise docker_utils.DCMDockerPullException(
                    repo=self.args.repository,
                    tag=self.args.tag,
                    error_msg=j_obj['error'])
        for k in id_map:
            dcm_logger.log_to_dcm_console_job_details(
                job_name=self.name, details="pulled " + id_map[k])
        return plugin_base.PluginReply(
            0, reply_type="docker_pull", reply_object=None)


def load_plugin(conf, job_id, items_map, name, arguments):
    return PullRepo(conf, job_id, items_map, name, arguments)
