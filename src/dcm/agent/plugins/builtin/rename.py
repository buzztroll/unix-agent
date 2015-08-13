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
import re

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.exceptions as plugin_exceptions
import dcm.agent.plugins.api.utils as plugin_utils


_g_logger = logging.getLogger(__name__)


def _is_legal(proposed_name):
    if len(proposed_name) > 255:
        raise plugin_exceptions.AgentPluginParameterBadValueException(
            "rename", "serverName", "less than 255")

    regex = ("^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)"
             "*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$")
    allowed = re.compile(regex)
    if allowed is None:
        raise plugin_exceptions.AgentPluginParameterBadValueException(
            "rename", "serverName", "a legal hostname")


class Rename(plugin_base.ScriptPlugin):

    protocol_arguments = {
        "serverName":
        ("The host name to which this server will be set.",
         True, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Rename, self).__init__(
            conf, job_id, items_map, name, arguments)

        _is_legal(arguments["serverName"])
        self.ordered_param_list = [arguments["serverName"]]

    def run(self):
        private_ips = self.conf.meta_data_object.get_ipv4_addresses()
        if not private_ips:
            return plugin_base.PluginReply(
                1, error_message="No IP Address was found")

        self.ordered_param_list.append(private_ips[0])
        plugin_utils.log_to_dcm_console_job_details(
            job_name=self.name, details=
            "Renaming the server to %s with the local IP %s"
            % (self.args.serverName, private_ips[0]))

        return super(Rename, self).run()


def load_plugin(conf, job_id, items_map, name, arguments):
    return Rename(conf, job_id, items_map, name, arguments)
