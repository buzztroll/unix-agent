import calendar
import logging
import Queue
import random
import threading
import time

import dcm.agent.jobs as jobs


# TODO handle thread safety

_g_logger = logging.getLogger(__name__)


class JobStatus(object):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"


class NewLongJob(object):
    def __init__(self, items_map, name, arguments, job_id, request_id):
        self.items_map = items_map
        self.name = name
        self.arguments = arguments
        self.job_id = job_id
        self.request_id = request_id


class JobReply(object):
    def __init__(self, job_id):
        self.job_id = job_id
        self.job_status = JobStatus.RUNNING
        self.start_date = calendar.timegm(time.gmtime())
        self.reply_doc = None
        self.end_date = None
        self.error = None

class JobRunner(threading.Thread):

    def __init__(self, queue, reply_queue):
        super(JobRunner, self).__init__()
        self._queue = queue
        self._exit = threading.Event()
        self._current_job = None
        self._reply_queue = reply_queue

    # It should be safe to call done without a lock
    def done(self):
        _g_logger.debug("done() called on worker %s .." % self.getName())
        self._exit.set()
        if self._current_job is not None:
            self._current_job.cancel()

    def run(self):
        _g_logger.info("Job runner %s thread starting." % self.getName())

        while not self._exit.is_set():
            try:
                work = self._queue.get(True, 1)

                try:
                    job_reply = JobReply(work.job_id)
                    self._reply_queue.put(job_reply)

                    plugin = jobs.load_python_module(
                        work.items_map["module_name"],
                        work.request_id,
                        work.items_map,
                        work.name,
                        work.arguments)

                    job_reply.reply_doc = plugin.run()
                except Exception as ex:
                    job_reply.error = ex.message
                    job_reply.job_status = JobStatus.ERROR
                else:
                    job_reply.job_status = JobStatus.COMPLETE
                finally:
                    job_reply.end_date = calendar.timegm(time.gmtime())
                    self._reply_queue.put(job_reply)

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
        self._reply_queue = Queue.Queue()
        self._runner_list = []
        for i in range(conf.workers_long_runner_threads):
            jr = JobRunner(self._run_queue, self._reply_queue)
            self._runner_list.append(jr)
            jr.start()
        self._timers = []

    def shutdown(self):
        # IF we want to make sure the queue is empty we must call
        # self._run_queue.join()
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
        module_name = items_map["module"]

        plugin = jobs.load_python_module(
            module_name, conf, request_id, items_map, name, arguments)

        self._lock.lock()
        try:
            self._job_id = self._job_id + 1
            new_job = NewLongJob(
                items_map, name, arguments, self._job_id, request_id)
            detached_job = DetachedJob(self._conf, self,
                                       plugin, name, arguments)
            self._job_table[detached_job.get_job_id()] = detached_job
            self._run_queue.put(new_job)
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

    def poll(self):
        try:
            work_reply = self._reply_queue.get(True, 1)
            self._lock.lock()
            try:
                jd = self._job_table[work_reply.job_id]
                jd.update(work_reply)
                if jd._job_status == JobStatus.ERROR or jd._job_status == JobStatus.COMPLETE:
                    self.job_complete(work_reply.job_id)
            except Exception as ex:
                return None
            finally:
                self._lock.unlock()
        except Queue.Empty:
            pass


class DetachedJob(object):

    def __init__(self, conf, job_id, plugin, command_name, arguments):
        self._customer_id = conf.customer_id
        self._description = command_name
        self._start_date = 0
        self._end_date = 0
        self._job_id = job_id
        self._job_status = JobStatus.WAITING
        self._message = None
        self._plugin = plugin
        self._command_name = command_name
        self._arguments = arguments
        self._error = None
        self._reply_doc = None

    def update(self, work_reply):
        self._job_status = work_reply.job_status
        self._start_date = work_reply.start_date
        self._reply_doc = work_reply.reply_doc
        self._end_date = work_reply.end_date
        self._error = work_reply.error

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
