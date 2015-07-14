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
