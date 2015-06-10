import os
import sys
import unittest
import uuid

import dcm.agent.config as config
import dcm.agent.systemstats as systemstats
import dcm.agent.jobs.builtin.init_system_stat as init_system_stat
import dcm.agent.jobs.builtin.get_system_stat as get_system_stat
import dcm.agent.jobs.builtin.delete_system_stat as delete_system_stat

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
                     "checkInterval": check_interval
        }

        plugin = init_system_stat.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "init_system_stat", arguments)
        result = plugin.run()
        self.assertEqual(result['return_code'], 0)

        try:
            event_space.poll(timeblock=check_interval*(hold_count+1))

            arguments = {"statName": stat_name}
            plugin = get_system_stat.load_plugin(
                self.conf_obj, str(uuid.uuid4()),
                {}, "get_system_stat", arguments)
            result = plugin.run()
            self.assertEqual(result['return_code'], 0)
            self.assertEqual(result['reply_type'], 'cpu_idle_stat_array')
            ro = result['reply_object']
            self.assertEqual(len(ro['status']), hold_count)

            arguments = {"statName": stat_name}
            plugin = delete_system_stat.load_plugin(
                self.conf_obj, str(uuid.uuid4()),
                {}, "delete_system_stat", arguments)
            result = plugin.run()
            self.assertEqual(result['return_code'], 0)
        finally:
            try:
                systemstats.stop_stats(stat_name)
            except Exception as ex:
                print(str(ex))