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
import os
import sys
import unittest
import uuid

import dcm.agent.config as config
import dcm.agent.systemstats as systemstats
import dcm.agent.plugins.builtin.init_system_stat as init_system_stat
import dcm.agent.plugins.builtin.get_system_stat as get_system_stat
import dcm.agent.plugins.builtin.delete_system_stat as delete_system_stat

from dcm.agent.events.globals import global_space as event_space


class TestSystemStatPlugin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        basedir = os.path.dirname((os.path.dirname(__file__)))
        cls.test_conf_path = \
            os.path.join(basedir, "etc", "agent.conf")
        cls.conf_obj = config.AgentConfig([cls.test_conf_path])

    def test_file_run(self):
        stat_name = str(uuid.uuid4())
        hold_count = 5
        check_interval = 0.1
        # we are now setup for the test
        arguments = {"statType": "cpu-idle",
                     "statName": stat_name,
                     "holdCount": hold_count,
                     "checkInterval": check_interval}

        plugin = init_system_stat.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "init_system_stat", arguments)
        result = plugin.run()
        result = result.get_reply_doc()
        self.assertEqual(result['return_code'], 0)

        try:
            event_space.poll(timeblock=check_interval*(hold_count+1))

            arguments = {"statName": stat_name}
            plugin = get_system_stat.load_plugin(
                self.conf_obj, str(uuid.uuid4()),
                {}, "get_system_stat", arguments)
            result = plugin.run()
            result = result.get_reply_doc()
            self.assertEqual(result['return_code'], 0)
            self.assertEqual(result['reply_type'], 'cpu_idle_stat_array')
            ro = result['reply_object']
            self.assertEqual(len(ro['status']), hold_count)

            arguments = {"statName": stat_name}
            plugin = delete_system_stat.load_plugin(
                self.conf_obj, str(uuid.uuid4()),
                {}, "delete_system_stat", arguments)
            result = plugin.run()
            result = result.get_reply_doc()
            self.assertEqual(result['return_code'], 0)
        finally:
            try:
                systemstats.stop_stats(stat_name)
            except Exception as ex:
                print(str(ex))
