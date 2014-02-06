import logging
import multiprocessing
import subprocess


_g_logger = logging.getLogger(__name__)


class JobRunnerWorker(multiprocessing.Process):

    def __init__(self, pipe):
        super(JobRunnerWorker, self).__init__()
        _g_logger.debug("Child job runner starting")
        self._pipe = pipe
        self._exit = multiprocessing.Event()

    def done(self):
        _g_logger.debug("Child job runner shutting down")
        self._exit.set()
        self._pipe.close()

    def run(self):
        try:
            while not self._exit.is_set():
                if self._pipe.poll(1):
                    cmd = self._pipe.recv()
                    if cmd is None:
                        continue;
                    try:
                        _g_logger.debug("Child runner starting the script %s" % cmd)

                        process = subprocess.Popen(cmd,
                                           shell=True,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           bufsize=0,
                                           env={},
                                           close_fds=True)
                        stdout, stderr = process.communicate()
                        rc = process.returncode

                        _g_logger.info("command %s:  STDOUT: %s" %(cmd, stdout))
                        _g_logger.info("STDERR: %s " % stderr)
                        _g_logger.info("Return code: " + str(rc))
                    except Exception as ex:
                        _g_logger.exception("Failed to run the script %s : %s",
                                   (str(cmd), str(ex)))
                        rc = 1
                        stdout = None
                        stderr = ex.message

                    except:
                        _g_logger.exception("Failed to run the script %s" % cmd)
                        rc = 2
                        stdout = None
                        stderr = "An unknown error occurred when attempting to " \
                                 "run %s" % cmd
                    finally:
                        _g_logger.debug("Completed the script %s" % cmd)

                    self._pipe.send((rc, stdout, stderr))
        except EOFError as eofEx:
            _g_logger.error(
                "The pipe to the processes runner was disconnected")
        except Exception as ex:
            _g_logger.error(ex)
            _g_logger.exception("The child runner failed")
        finally:
            _g_logger.debug("The child runner has ended.")


class JobRunner(object):

    def __init__(self):
        _g_logger.debug("Starting the child")

        self._parent_conn, self._child_conn = multiprocessing.Pipe()
        self._child = JobRunnerWorker(self._child_conn)
        self._child.start()

    def run_command(self, cmd):
        _g_logger.debug("Sending the command %s to the child runner" % cmd)
        self._parent_conn.send(cmd)
        (rc, stdout, stderr) = self._parent_conn.recv()
        return (stdout, stderr, rc)

    def shutdown(self):
        _g_logger.debug("Job runner shutting down")
        self._child.done()
        self._parent_conn.close()
        self._child_conn.close()
        self._child.join()

