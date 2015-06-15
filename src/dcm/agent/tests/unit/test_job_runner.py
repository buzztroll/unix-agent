from collections import namedtuple
import os
import queue
import threading
import unittest
import uuid
import mock
import time

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


class TestJobRunnerChild(unittest.TestCase):

    def test_none_from_pipe(self):
        pipe = mock.Mock()
        pipe.poll.return_value = True
        pipe.recv.return_value = None
        jr = job_runner.JobRunnerWorker(pipe, g_fake_conf)
        tr = threading.Thread(target=jr.run)
        tr.start()
        time.sleep(0.1)
        jr.done()
        tr.join()

    def test_basic_sync_job(self):
        msg = str(uuid.uuid4())
        wrk = (job_runner.JobRunnerWorker.CMD_JOB, ["/bin/echo", msg], "/", {})
        pipe = mock.Mock()
        pipe.poll.return_value = True
        pipe.recv.return_value = wrk
        jr = job_runner.JobRunnerWorker(pipe, g_fake_conf)
        tr = threading.Thread(target=jr.run)
        tr.start()
        time.sleep(0.05)
        jr.done()
        tr.join()
        # check that we got good stuff back
        args, kwargs = pipe.send.call_args_list[0]
        self.assertEqual(args[0][0], 0)

    def test_bad_sync_job(self):
        msg = str(uuid.uuid4())
        wrk = (job_runner.JobRunnerWorker.CMD_JOB, ["notreal"], "/", {})
        pipe = mock.Mock()
        pipe.poll.return_value = True
        pipe.recv.return_value = wrk
        jr = job_runner.JobRunnerWorker(pipe, g_fake_conf)
        tr = threading.Thread(target=jr.run)
        tr.start()
        time.sleep(0.05)
        jr.done()
        tr.join()
        # check that we got good stuff back
        args, kwargs = pipe.send.call_args_list[0]
        self.assertEqual(args[0][0], 1)

    def test_unknown_job(self):
        msg = str(uuid.uuid4())
        wrk = ("NOTREAL", ["/bin/echo", msg], "/", {})
        pipe = mock.Mock()
        pipe.poll.return_value = True
        pipe.recv.return_value = wrk
        pipe.send.side_effect = Exception("BadMessage")
        jr = job_runner.JobRunnerWorker(pipe, g_fake_conf)
        tr = threading.Thread(target=jr.run)
        tr.start()
        time.sleep(0.05)
        jr.done()
        tr.join()
        # check that we got good stuff back
        self.assertEqual(pipe.send.call_count, 0)

    def test_poll_job(self):

        pass_force_in_results = queue.Queue()

        def poller():
            try:
                return pass_force_in_results.get(timeout=1.0)
            except:
                return None

        msg = str(uuid.uuid4())
        wrk = (job_runner.JobRunnerWorker.CMD_JOB, ["/bin/echo", msg], "/", {})
        pass_force_in_results.put(wrk)
        pipe = mock.Mock()
        pipe.poll.side_effect = lambda x: pass_force_in_results.qsize() > 0
        pipe.recv.side_effect = poller
        jr = job_runner.JobRunnerWorker(pipe, g_fake_conf)
        tr = threading.Thread(target=jr.run)
        tr.start()
        # check that we got good stuff back
        time.sleep(0.2)
        args, kwargs = pipe.send.call_args_list[0]
        self.assertEqual(args[0][0], 0)
        pid = args[0][1]
        wrk = (job_runner.JobRunnerWorker.CMD_POLL_JOB, pid)
        pass_force_in_results.put(wrk)
        time.sleep(0.2)

        jr.done()
        tr.join()
        args, kwargs = pipe.send.call_args_list[1]
        self.assertEqual(args[0][0], 0)
        self.assertEqual(args[0][1].strip(), msg)
