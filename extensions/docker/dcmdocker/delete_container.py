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
