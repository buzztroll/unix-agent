import logging
import multiprocessing
import os
import subprocess
import tempfile
import threading
from dcm.agent import system_lock
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
                                         #shell=True,
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
        self._svc_lock = system_lock.ChildProcessLockMgr(conf)
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
        if rc == None:
            return (rc, None, None)
        del self._jobs[pid]
        stdout = sync_job.get_stdout()
        stderr = sync_job.get_stderr()

        _g_logger.info("command %s:  STDOUT: %s" %
                       (sync_job.cmd, unicode(stdout, errors='ignore')))
        _g_logger.info("STDERR: %s " % unicode(stderr, errors='ignore'))
        _g_logger.info("Return code: " + str(rc))

        return (rc, stdout, stderr)

    def _lock(self, wrk):
        (_, timeout, lock_fs) = wrk
        try:
            self._svc_lock.lock(timeout, lock_fs)
            reply = (0, "")
        except Exception as ex:
            reply = (1, ex.message)
        return reply

    def _unlock(self, wrk):
        try:
            self._svc_lock.unlock()
            reply = (0, "")
        except Exception as ex:
            reply = (1, ex.message)
        return reply

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
                    elif wrk[0] == JobRunnerWorker.LOCK_JOB:
                        reply = self._lock(wrk)
                    elif wrk[0] == JobRunnerWorker.CMD_POLL_JOB:
                        reply = self._poll_job(wrk)
                    elif wrk[0] == JobRunnerWorker.UNLOCK_JOB:
                        reply = self._unlock(wrk)
                    else:
                        _g_logger.error(
                            "An unknown work type was received %s" % wrk[0])
                        continue
                    self._pipe.send(reply)
        except EOFError as eofEx:
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
        _g_logger.info("Sending the command %s to the child runner" % cmd)
        (rc, pid, msg) = self._send_receive_safe((JobRunnerWorker.CMD_JOB, cmd, cwd, env))
        if rc != 0:
            _g_logger.error("The command failed to start %s" % msg)
            return ("", msg, rc)

        # we need to busy wait poll for a reply so that we can multiplex
        # work over the pipe
        done = False
        while not done:
            (rc, stdout, stderr) = self._send_receive_safe(
                (JobRunnerWorker.CMD_POLL_JOB, pid))
            if rc is not None:
                done = True
            else:
                time.sleep(0.5)

        # If it started we will start waiting for it to finish
        _g_logger.info("Output from the command %s. rc=%d, stdout=%s, "
                       "stderr=%s" % (cmd, rc, stdout, stderr))
        return (stdout, stderr, rc)

    def lock(self, timeout, lock_fs):
        _g_logger.debug("Sending lock the child runner")
        (rc, message) = self._send_receive_safe(
            (JobRunnerWorker.LOCK_JOB, timeout, lock_fs))
        if rc != 0:
            raise Exception(message)

    def unlock(self):
        _g_logger.debug("Sending unlock the child runner")
        (rc, message) = self._send_receive_safe(
            (JobRunnerWorker.UNLOCK_JOB, 1))
        if rc != 0:
            raise Exception(message)

    def shutdown(self):
        _g_logger.debug("Job runner shutting down")
        self._child.done()
        self._parent_conn.close()
        self._child_conn.close()
        self._child.join()
