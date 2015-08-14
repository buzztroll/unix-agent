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
import unittest
import uuid

import dcm.agent.exceptions as exceptions
import dcm.agent.systemstats as systemstats


class TestSystemStats(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        systemstats.clean_up_all()

    def test_get_system_stat_not_exists(self):
        self.assertRaises(
            exceptions.AgentOptionValueNotSetException,
            systemstats.get_stats,
            "somename")

    def test_stop_system_stat_not_exists(self):
        self.assertRaises(
            exceptions.AgentOptionValueNotSetException,
            systemstats.stop_stats,
            "somename")

    def test_start_system_stat_bad_type(self):
        name = str(uuid.uuid4())
        self.assertRaises(
            exceptions.AgentOptionValueException,
            systemstats.start_new_system_stat,
            name,
            "no_good",
            10,
            10.0)

    def test_system_stat_happy_path_cpu_idle(self):
        hold_count = 10
        interval = 0.1
        name = str(uuid.uuid4())
        systemstats.start_new_system_stat(
            name,
            "cpu-idle",
            hold_count,
            interval)
        time.sleep((hold_count + 2) * interval)
        stats_d = systemstats.get_stats(name)
        self.assertEqual(len(stats_d['status']), hold_count)
        systemstats.stop_stats(name)

    def test_system_stat_two_cpu_idle(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())
        hold_count2 = int(hold_count1 / 2)
        interval2 = interval1 * 2
        name2 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "cpu-idle",
            hold_count1,
            interval1)
        systemstats.start_new_system_stat(
            name2,
            "cpu-idle",
            hold_count2,
            interval2)

        time.sleep((hold_count1 + 2) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        time.sleep((hold_count2 + 2) * interval2)
        stats_d = systemstats.get_stats(name2)
        self.assertEqual(len(stats_d['status']), hold_count2)

        systemstats.stop_stats(name1)
        systemstats.stop_stats(name2)

    def test_system_stat_stop_twice(self):
        hold_count = 10
        interval = 0.1
        name = str(uuid.uuid4())
        systemstats.start_new_system_stat(
            name,
            "cpu-idle",
            hold_count,
            interval)
        systemstats.stop_stats(name)
        self.assertRaises(
            exceptions.AgentOptionValueNotSetException,
            systemstats.stop_stats,
            name)


class TestAgentVerboseSystemStats(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        systemstats.clean_up_all()

    def test_basic_verbose_stat(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "system-stats",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 2) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('cpu-load', ent_1)
        self.assertIn('net-bytes-in', ent_1)
        self.assertIn('net-bytes-out', ent_1)
        self.assertIn('disk-read-bytes', ent_1)
        self.assertIn('disk-write-bytes', ent_1)
        self.assertIn('disk-read-ops', ent_1)
        self.assertIn('disk-write-ops', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)

    def test_basic_read_ops(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "disk-read-ops",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 3) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('disk-read-ops', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)

    def test_basic_write_ops(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "disk-write-ops",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 3) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('disk-write-ops', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)

    def test_basic_read_bytes(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "disk-read-bytes",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 3) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('disk-read-bytes', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)

    def test_basic_write_bytes(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "disk-write-bytes",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 3) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('disk-write-bytes', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)

    def test_basic_net_in(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "net-bytes-in",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 3) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('net-bytes-in', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)

    def test_basic_net_out(self):
        hold_count1 = 10
        interval1 = 0.1
        name1 = str(uuid.uuid4())

        systemstats.start_new_system_stat(
            name1,
            "net-bytes-out",
            hold_count1,
            interval1)

        time.sleep((hold_count1 + 3) * interval1)
        stats_d = systemstats.get_stats(name1)
        self.assertEqual(len(stats_d['status']), hold_count1)

        ent_1 = stats_d['status'][0]
        self.assertIn('net-bytes-out', ent_1)
        self.assertIn('timestamp', ent_1)
        systemstats.stop_stats(name1)
