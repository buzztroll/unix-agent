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
import logging
import uuid

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.pages as pages
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class GetLogContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "stdout": ("", False, bool, True),
        "stderr": ("", False, bool, False),
        "timestamps": ("", False, bool, False),
        "page_token": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetLogContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        if self.args.page_token is None:
            out = self.docker_conn.logs(self.args.container,
                                        stdout=self.args.stdout,
                                        stderr=self.args.stderr,
                                        stream=False,
                                        timestamps=self.args.timestamps)
            token = str(uuid.uuid4()).replace("-", "")
            pager = pages.StringPage(12*1024, out)
            self.conf.page_monitor.new_pager(pager, token)
        else:
            token = self.args.page_token

        page, token = self.conf.page_monitor.get_next_page(token)
        out = {'next_token': token, 'log_data': page}
        return plugin_base.PluginReply(
            0, reply_type="docker_logs", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetLogContainer(conf, job_id, items_map, name, arguments)
