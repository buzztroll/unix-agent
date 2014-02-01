import Queue
import calendar
import logging
import random
import threading
import time

import dcm.agent.jobs as jobs


# TODO handle thread safety

_g_logger = logging.getLogger(__name__)


class JobRunner(threading.Thread):

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self._queue = queue
        self._done = False
        self._current_job = None

    # It should be safe to call done without a lock
    def done(self):
        _g_logger.debug("done() called on worker %s .." % self.getName())
        self._done = True
        if self._current_job is not None:
            self._current_job.cancel()

    def run(self):
        _g_logger.info("Job runner %s thread starting." % self.getName())

        while not self._done:
            try:
                self._current_job = self.worker_queue.get(True, 1)
                self._current_job.run()
            except Queue.Empty:
                pass
            except:
                _g_logger.exception(
                    "Something went wrong processing the job")
            finally:
                self._current_job = None

        _g_logger.info("Job runner %s thread ending." % self.getName())


class LongRunner(object):

    def __init__(self, conf):
        self._job_table = {}
        self._job_id = 0
        self._lock = threading.RLock()
        self._conf = conf
        self._run_queue = Queue.Queue()
        self._runner_list = []
        for i in range(conf.long_runner_threads):
            jr = JobRunner(self._run_queue)
            self._runner_list.append(jr)
            jr.start()
        self._timers = []

    def shutdown(self):
        self._run_queue.join()
        for r in self._runner_list:
            _g_logger.debug("Stopping worker %s" % str(r))
            r.done()
            r.join()
            _g_logger.debug("Runner %s is done" % str(r))
        _g_logger.info("The dispatcher is closed.")
        for t in self._timers:
            try:
                t.cancel()
            except:
                pass
            t.join()

    def start_new_job(self, conf, request_id, items_map,
                      name, arguments):
        module_name = items_map["worker_module"]
        long_runner = items_map["long_runner"]

        plugin = jobs.load_python_module(
            module_name, conf, request_id, items_map, name, arguments)

        self._lock.lock()
        try:
            self._job_id = self._job_id + 1
            detached_job = DetachedJob(self._conf, long_runner,
                                       plugin, name, arguments)
            self._job_table[detached_job.get_job_id()] = detached_job
            self._run_queue.put(detached_job)
            return detached_job
        finally:
            self._lock.unlock()

    def job_complete(self, job_id):
        if self._conf.jobs_retain_job_time == 0:
            return
        t = threading.Timer(self._conf.jobs_retain_job_time,
                            self._job_cleanup, job_id)
        self._timers.append(t)
        t.start()

    def _job_cleanup(self, job_id):
        self._lock.lock()
        try:
            _g_logger.debug("Removing job %d for the table" % job_id)
            del self._job_table[job_id]
        finally:
            self._lock.unlock()
        pass

    def lookup_job(self, job_id):

        self._lock.lock()
        try:
            return self._job_table[job_id]
        except Exception as ex:
            return None
        finally:
            self._lock.unlock()


class JobStatus(object):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"


class DetachedJob(object):

    def __init__(self, conf, long_runner, plugin, command_name, arguments):
        self._customer_id = conf.customer_id
        self._description = command_name
        self._start_date = 0
        self._end_date = 0
        self._job_id = random.randint()
        self._job_status = JobStatus.WAITING
        self._message = None
        self._plugin = plugin
        self._command_name = command_name
        self._arguments = arguments
        self._error = None
        self._reply_doc = None
        self._long_runner = long_runner

    def get_job_id(self):
        return self._job_id

    def get_message_payload(self):
        reply_object = {
            "customer_id": self._customer_id,
            "description": self._description,
            "job_id": self._job_id,
            "job_status": self._job_status,
            "message": self._message,
            "start_date": self._start_date,
            "end_date": self._end_date,
        }
        return reply_object

    def run(self):
        try:
            self._job_status = JobStatus.RUNNING
            self._start_date = calendar.timegm(time.gmtime())
            # run the command
            self._reply_doc = self.plugin.run()
        except Exception as ex:
            self._error = ex
            self._job_status = JobStatus.ERROR
        else:
            self._job_status = JobStatus.COMPLETE
        finally:
            self._end_date = calendar.timegm(time.gmtime())
            self._long_runner.job_complete(self._job_id)

    def cancel(self):
        pass





