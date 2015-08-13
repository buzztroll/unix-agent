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
import time

import dcm.agent.plugins.api.base as plugin_base


class CountSleepExample(plugin_base.Plugin):
    protocol_arguments = {
        "count": ("The number of times to loop and sleep", True, int, 10),
        "sleepTime": ("The number of seconds to sleep ever iteration",
                      True, float, 1.0)
    }
    long_runner = True
    command_name = "count_sleep_example"

    def run(self):
        for _ in range(self.args.count):
            time.sleep(self.args.sleepTime)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return CountSleepExample(conf, job_id, items_map, name, arguments)
