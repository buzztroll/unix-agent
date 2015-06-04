from collections import namedtuple
import os
import threading
import unittest

import dcm.agent.job_runner as job_runner


FakeConf = namedtuple('FakeConf', 'platform_name platform_version')

g_fake_conf = FakeConf("ubuntu", "14.04")


class TestJobRunner(unittest.TestCase):

    def setUp(self):
        self.jr = job_runner.JobRunner(g_fake_conf)

    def tearDown(self):
        self.jr.shutdown()

    def test_single_fast(self):
        tester_val = "SOME_VALUE"
        (stdout, stderr, rc) = self.jr.run_command(["/bin/echo", tester_val])
        self.assertEqual(0, rc)
        self.assertEqual(tester_val, stdout.strip())

    def test_cwd(self):
        cwd = os.path.expanduser("~")
        (stdout, stderr, rc) = self.jr.run_command(["/bin/pwd"], cwd=cwd)
        self.assertEqual(0, rc)
        self.assertEquals(cwd, stdout.strip())

    def test_env(self):
        akey = "SOMEENVKEY"
        aval = "SOMEVALUE"
        tst_env = {akey: aval}
        (stdout, stderr, rc) = self.jr.run_command(["/usr/bin/env"],
                                                   env=tst_env)
        self.assertTrue(stdout.find(akey) >= 0)
        self.assertTrue(stdout.find(aval) >= 0)

    def test_long_command(self):
        (stdout, stderr, rc) = self.jr.run_command(["/bin/sleep", "5"])
        self.assertEqual(0, rc)

    def test_many_overlap(self):

        def _func(tester_val):
            (stdout, stderr, rc) = self.jr.run_command(
                ["/bin/echo", tester_val])
            self.assertEqual(0, rc)
            self.assertEqual(tester_val, stdout.strip())

        def _sleep_func():
            (stdout, stderr, rc) = self.jr.run_command(["/bin/sleep", "5"])
            print(stderr)
            print(stdout)
            self.assertEqual(0, rc)

        threads = []
        for i in range(50):
            t = threading.Thread(target=_func, args=("WORKER_%d" % i,))
            threads.append(t)
            t.start()
            # sleep for overlap
            t = threading.Thread(target=_sleep_func)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
