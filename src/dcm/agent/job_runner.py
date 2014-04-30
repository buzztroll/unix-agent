import logging
import multiprocessing
import subprocess
from dcm.agent import system_lock


_g_logger = logging.getLogger(__name__)


class JobRunnerWorker(multiprocessing.Process):

    SYNC_JOB = "SYNC_JOB"
    LOCK_JOB = "LOCK_JOB"
    UNLOCK_JOB = "UNLOCK_JOB"

    def __init__(self, pipe, conf):
        super(JobRunnerWorker, self).__init__()
        _g_logger.info("Child job runner starting")
        self._pipe = pipe
        self._exit = multiprocessing.Event()
        self._svc_lock = system_lock.ChildProcessLockMgr(conf)
        self._conf = conf

    def done(self):
        _g_logger.info("Child job runner shutting down")
        self._exit.set()
        self._pipe.close()

    def _sync_job(self, wrk):
        (msg_type, cmd, cwd, env) = wrk
        try:
            _g_logger.info("Child runner starting the script %s ;"
                           " env=%s"
                           % (cmd, env))

            process = subprocess.Popen(cmd,
                                       shell=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       cwd=cwd,
                                       env=env)
            stdout, stderr = process.communicate()
            rc = process.returncode

            _g_logger.info("command %s:  STDOUT: %s" %
                           (cmd, stdout))
            _g_logger.info("STDERR: %s " % stderr)
            _g_logger.info("Return code: " + str(rc))
        except Exception as ex:
            _g_logger.exception("Failed to run the script %s : %s"
                                % (str(cmd), str(ex)))
            rc = 1
            stdout = None
            stderr = ex.message
        except:
            _g_logger.exception("Failed to run the script %s"
                                % cmd)
            rc = 2
            stdout = None
            stderr = "An unknown error occurred when attempting " \
                     "to run %s" % cmd
        finally:
            _g_logger.debug("Completed the script %s" % cmd)
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
                    if wrk[0] == JobRunnerWorker.SYNC_JOB:
                        reply = self._sync_job(wrk)
                    elif wrk[0] == JobRunnerWorker.LOCK_JOB:
                        reply = self._lock(wrk)
                    elif wrk[0] == JobRunnerWorker.UNLOCK_JOB:
                        reply = self._unlock(wrk)
                    else:
                        _g_logger.error("An unknown work type was received %s" %
                                        wrk[0])
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

    def run_command(self, cmd, cwd=None, env=None):
        if type(cmd) == list or type(cmd) == tuple:
            cmd = " ".join([str(i) for i in cmd])

        _g_logger.debug("Sending the command %s to the child runner" % cmd)
        self._parent_conn.send((JobRunnerWorker.SYNC_JOB, cmd, cwd, env))
        (rc, stdout, stderr) = self._parent_conn.recv()
        return (stdout, stderr, rc)

    def lock(self, timeout, lock_fs):
        _g_logger.debug("Sending lock the child runner")
        self._parent_conn.send((JobRunnerWorker.LOCK_JOB, timeout, lock_fs))
        (rc, message) = self._parent_conn.recv()
        if rc != 0:
            raise Exception(message)

    def unlock(self):
        _g_logger.debug("Sending unlock the child runner")
        self._parent_conn.send((JobRunnerWorker.UNLOCK_JOB, 1))
        (rc, message) = self._parent_conn.recv()
        if rc != 0:
            raise Exception(message)

    def shutdown(self):
        _g_logger.debug("Job runner shutting down")
        self._child.done()
        self._parent_conn.close()
        self._child_conn.close()
        self._child.join()
