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
import multiprocessing
import platform
import psutil

import dcm.agent.plugins.api.base as plugin_base


class GetAgentData(plugin_base.Plugin):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetAgentData, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        load = psutil.cpu_percent(0.1)  # NOTE(buzztroll) blocks for 0.1s
        mem_usage = psutil.phymem_usage()
        reply_object = {
            "cpu_count": multiprocessing.cpu_count(),
            "cpu_load": load,
            "current_ram": mem_usage.used,
            "max_ram": mem_usage.total,
            "processes": len(psutil.get_pid_list()),
            "platform": platform.platform(),
            # NOTE(buzztroll) I am not sure what to do with server state.  The
            # available options suggest error or contention.  I think if we get
            # to this point in system those values should all be invalid.
            # meaning we should have rejected a new command long ago.
            "server_state": "OK"
        }
        return plugin_base.PluginReply(
            0, reply_type="agent_data", reply_object=reply_object)


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetAgentData(conf, job_id, items_map, name, arguments)
