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

import dcm.agent.exceptions as exceptions
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.utils as plugin_utils

_g_logger = logging.getLogger(__name__)


class RemoveUser(plugin_base.ScriptPlugin):

    protocol_arguments = {
        "userId":
        ("The unix account name of the user to remove",
         True, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RemoveUser, self).__init__(
            conf, job_id, items_map, name, arguments)
        self.ordered_param_list = [self.args.userId]

    def run(self):
        command = [self.conf.get_script_location("removeUser"),
                   self.args.userId]
        (stdout, stderr, rc) = plugin_utils.run_command(self.conf, command, with_sudo=True)
        if rc != 0:
            raise exceptions.AgentExecutableException(
                    command, rc, stdout, stderr)
        return plugin_base.PluginReply(rc, message="job removeUser succeeded.")


def load_plugin(conf, job_id, items_map, name, arguments):
    return RemoveUser(conf, job_id, items_map, name, arguments)
