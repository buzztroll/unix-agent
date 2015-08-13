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
import os

import dcm.agent.exceptions as exceptions
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class GetDeviceMappings(plugin_base.Plugin):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetDeviceMappings, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name)]

    def run(self):
        try:
            device_mapping_list = utils.get_device_mappings(self.conf)
        except exceptions.AgentExecutableException as ex:
            return plugin_base.PluginReply(1, message=str(ex))
        return plugin_base.PluginReply(
            0,
            reply_type="device_mapping_array",
            reply_object=device_mapping_list)


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetDeviceMappings(conf, job_id, items_map, name, arguments)
