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


class DockerCreateContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "image": ("", True, str, None),
        "command": ("", False, str, None),
        "hostname": ("", False, str, None),
        "user": ("", False, str, None),
        "mem_limit": ("", False, int, 0),
        "ports": ("", False, list, None),
        "environment": ("", False, dict, None),
        "memswap_limit": ("", False, int, 0),
        "name": ("", False, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerCreateContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.create_container(
            self.args.image,
            command=self.args.command,
            hostname=self.args.hostname,
            user=self.args.user,
            detach=True,
            stdin_open=False,
            tty=False,
            mem_limit=self.args.mem_limit,
            ports=self.args.ports,
            environment=self.args.environment,
            dns=None,
            volumes=None,
            volumes_from=None,
            network_disabled=False,
            name=self.args.name,
            entrypoint=None,
            cpu_shares=None,
            working_dir=None,
            memswap_limit=self.args.memswap_limit)
        return plugin_base.PluginReply(
            0, reply_type="docker_create_container", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return DockerCreateContainer(conf, job_id, items_map, name, arguments)


def get_features(conf):
    return {'docker': "1.1.2"}
