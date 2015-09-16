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
import multiprocessing
import os
import subprocess
import tempfile
import threading
import time


_g_logger = logging.getLogger(__name__)


class SyncJob(object):

    def __init__(self, cmd, cwd, env):

        self.cmd = cmd
        self._stdout, self._stdout_path = \
            tempfile.mkstemp(prefix="dcmagentoutput")
        self._stderr, self._stderr_path = \
            tempfile.mkstemp(prefix="dcmagentoutput")

        self._process = subprocess.Popen(cmd,
                                         stdout=self._stdout,
                                         stderr=self._stderr,
                                         cwd=cwd,
                                         env=env)

    def get_pid(self):
        return self._process.pid

    def poll(self):
        return self._process.poll()

    def get_stdout(self):
        with open(self._stdout_path, "r") as fptr:
            data = fptr.read()
        os.remove(self._stdout_path)
        return data

    def get_stderr(self):
        with open(self._stderr_path, "r") as fptr:
            data = fptr.read()
        os.remove(self._stderr_path)
        return data


class JobRunnerWorker(multiprocessing.Process):

    CMD_JOB = "CMD_JOB"
    CMD_POLL_JOB = "CMD_POLL_JOB"
    LOCK_JOB = "LOCK_JOB"
    UNLOCK_JOB = "UNLOCK_JOB"

    def __init__(self, pipe, conf):
        super(JobRunnerWorker, self).__init__()
        _g_logger.info("Child job runner starting")
        self._pipe = pipe
        self._exit = multiprocessing.Event()
        self._conf = conf
        self._jobs = {}

    def done(self):
        _g_logger.info("Child job runner shutting down")
        self._exit.set()
        self._pipe.close()

    def _sync_job(self, wrk):
        try:
            (msg_type, cmd, cwd, env) = wrk
            env['DCM_AGENT_PLATFORM_NAME'] = self._conf.platform_name
            env['DCM_AGENT_PLATFORM_VERSION'] = self._conf.platform_version
            _g_logger.info("Child runner starting the script %s ;"
                           " env=%s"
                           % (cmd, env))

            sync_job = SyncJob(cmd, cwd, env)
            pid = sync_job.get_pid()
            rc = 0
            msg = ""
            self._jobs[pid] = sync_job
        except Exception as ex:
            _g_logger.exception("Failed to run the script %s : %s"
                                % (str(cmd), str(ex)))
            rc = 1
            pid = -1
            msg = str(ex)
        except:
            _g_logger.exception("Failed to run the script %s"
                                % cmd)
            rc = 2
            pid = -1
            msg = "An unknown error occurred when attempting " \
                  "to run %s" % cmd
        return (rc, pid, msg)

    def _poll_job(self, wrk):
        pid = wrk[1]
        sync_job = self._jobs[pid]
        rc = sync_job.poll()
        if rc is None:
            return (rc, None, None)
        del self._jobs[pid]
        stdout = sync_job.get_stdout()
        stderr = sync_job.get_stderr()

        _g_logger.info("command %s:  STDOUT: %s" %
                       (sync_job.cmd, stdout))
        _g_logger.info("STDERR: %s " % stderr)
        _g_logger.info("Return code: " + str(rc))

        return (rc, stdout, stderr)

    def run(self):
        try:
            while not self._exit.is_set():
                if self._pipe.poll(1):
                    wrk = self._pipe.recv()
                    if wrk is None:
                        continue
                    _g_logger.debug("Received job type %s" % wrk[0])
                    if wrk[0] == JobRunnerWorker.CMD_JOB:
                        reply = self._sync_job(wrk)
                    elif wrk[0] == JobRunnerWorker.CMD_POLL_JOB:
                        reply = self._poll_job(wrk)
                    else:
                        _g_logger.error(
                            "An unknown work type was received %s" % wrk[0])
                        continue
                    self._pipe.send(reply)
        except EOFError:
            _g_logger.error(
                "The pipe to the processes runner was disconnected")
        except Exception as ex:
            _g_logger.error(ex)
            _g_logger.exception("The child runner failed")
        finally:
            _g_logger.debug("The child runner has ended.")


class JobRunner(object):

    def __init__(self, conf):
        _g_logger.debug("Starting the child")

        self._parent_conn, self._child_conn = multiprocessing.Pipe()
        self._child = JobRunnerWorker(self._child_conn, conf)
        self._child.start()
        self._lock = threading.RLock()

    def _send_receive_safe(self, msg):
        self._lock.acquire()
        try:
            self._parent_conn.send(msg)
            return self._parent_conn.recv()
        finally:
            self._lock.release()

    def run_command(self, cmd, cwd=None, env=None):
        # if type(cmd) == list or type(cmd) == tuple:
        #     cmd = " ".join([str(i) for i in cmd])

        if env is None:
            env = {}
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   cwd=cwd,
                                   env=env)

        (stdout, stderr) = process.communicate()
        rc = process.wait()
        return (stdout, stderr, rc)

    def shutdown(self):
        _g_logger.debug("Job runner shutting down")
        self._child.done()
        self._parent_conn.close()
        self._child_conn.close()
        self._child.join()
