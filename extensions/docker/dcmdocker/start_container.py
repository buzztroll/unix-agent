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


class StartContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "port_bindings": ("", False, dict, None),
        "lxc_conf": ("", False, list, None),
        "links": ("", False, dict, None),
        "privileged": ("", False, bool, False),
        "publish_all_ports": ("", False, bool, False),
        "cap_add": ("", False, list, None),
        "cap_drop": ("", False, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StartContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        # make a list a tuple
        if self.args.port_bindings:
            for internal_port in self.args.port_bindings:
                binding_list = self.args.port_bindings[internal_port]
                new_binding_list = []
                for bind in binding_list:
                    host, port = bind
                    new_binding_list.append((host, port,))
                self.args.port_bindings[internal_port] = new_binding_list

        self.docker_conn.start(self.args.container,
                               port_bindings=self.args.port_bindings,
                               lxc_conf=self.args.lxc_conf,
                               links=self.args.links,
                               privileged=self.args.privileged,
                               publish_all_ports=self.args.publish_all_ports,
                               cap_add=self.args.cap_add,
                               cap_drop=self.args.cap_drop,
                               network_mode="bridge")
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return StartContainer(conf, job_id, items_map, name, arguments)
