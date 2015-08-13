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
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.systemstats as systemstats


class DeleteSystemStat(plugin_base.Plugin):

    protocol_arguments = {
        "statName": ("The name of the stat collector to query.",
                     True, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DeleteSystemStat, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        systemstats.stop_stats(self.args.statName)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return DeleteSystemStat(conf, job_id, items_map, name, arguments)
