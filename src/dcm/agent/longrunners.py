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
import calendar
import logging
import queue
import threading
import time
import urllib.parse
import urllib.error
import urllib.request

import dcm.agent.plugins.loader as plugin_loader

from dcm.agent.events.globals import global_space as dcm_events


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
        self.quit = False


class JobReply(object):
    def __init__(self, job_id):
        self.job_id = job_id
        self.job_status = JobStatus.RUNNING
        self.start_date = calendar.timegm(time.gmtime())
        self.reply_doc = None
        self.end_date = None
        self.error = None


class JobRunner(threading.Thread):

    def __init__(self, conf, queue, job_update_callback):
        super(JobRunner, self).__init__()
        self._queue = queue
        self._exit = threading.Event()
        self._current_job = None
        self._job_update_callback = job_update_callback
        self._conf = conf

    # It should be safe to call done without a lock
    def done(self):
        _g_logger.debug("done() called on worker %s .." % self.getName())
        self._exit.set()
        if self._current_job is not None:
            self._current_job.cancel()

    def run(self):
        _g_logger.info("Job runner %s thread starting." % self.getName())

        done = False
        while not done:
            try:
                work = self._queue.get(True)
                if work.quit:
                    done = True
                    continue

                try:
                    _g_logger.debug("Running the long job %s:%s" %
                                    (work.name, work.request_id))

                    job_reply = JobReply(work.job_id)
                    dcm_events.register_callback(
                        self._job_update_callback, args=[job_reply])

                    plugin = plugin_loader.load_python_module(
                        work.items_map["module_name"],
                        self._conf,
                        work.request_id,
                        work.items_map,
                        work.name,
                        work.arguments)

                    reply_obj = plugin.run()
                    job_reply.reply_doc = reply_obj.get_reply_doc()
                except Exception as ex:
                    _g_logger.exception("An error occurred")
                    job_reply.error = str(ex)
                    job_reply.job_status = JobStatus.ERROR
                else:
                    if job_reply.reply_doc is None:
                        job_reply.job_status = JobStatus.COMPLETE
                    elif job_reply.reply_doc["return_code"] == 0:
                        job_reply.job_status = JobStatus.COMPLETE
                    else:
                        job_reply.job_status = JobStatus.ERROR
                        job_reply.error = job_reply.reply_doc["message"]
                finally:
                    job_reply.end_date = calendar.timegm(time.gmtime())
                    dcm_events.register_callback(
                        self._job_update_callback, args=[job_reply])
                    _g_logger.debug("Completed the long job %s:%s "
                                    "STATUS=%s" % (work.name, work.request_id,
                                                   job_reply.job_status))

            except queue.Empty:
                _g_logger.exception("The queue was empty.  This shouldn't "
                                    "happen often")
            except Exception as ex:
                _g_logger.exception("Something went wrong processing the job")
            finally:
                self._current_job = None

        _g_logger.info("Job runner %s thread ending." % self.getName())


class LongRunner(object):

    def __init__(self, conf):
        self._job_table = {}
        self._job_id = 0
        self._lock = threading.RLock()
        self._conf = conf
        self._run_queue = queue.Queue()
        self._runner_list = []
        for i in range(conf.workers_long_runner_threads):
            jr = JobRunner(conf, self._run_queue, self.job_update_callback)
            self._runner_list.append(jr)
            jr.start()

    def shutdown(self):
        # IF we want to make sure the queue is empty we must call
        # self._run_queue.join()

        for i in range(len(self._runner_list)):
            quit_job = NewLongJob(None, None, None, None, None)
            quit_job.quit = True
            self._run_queue.put(quit_job)
        for r in self._runner_list:
            _g_logger.debug("Stopping worker %s" % str(r))
            r.done()
            r.join()
            _g_logger.debug("Runner %s is done" % str(r))
        _g_logger.info("The dispatcher is closed.")

    def start_new_job(self, conf, request_id, items_map,
                      name, arguments):
        module_name = items_map["module_name"]

        plugin = plugin_loader.load_python_module(
            module_name, conf, request_id, items_map, name, arguments)

        with self._lock:
            self._job_id += 1
            new_job = NewLongJob(
                items_map, name, arguments, self._job_id, request_id)
            detached_job = DetachedJob(self._conf, self._job_id,
                                       plugin, name, arguments)
            self._job_table[detached_job.get_job_id()] = detached_job
            _g_logger.debug("Starting new long job id=%s"
                            % str(detached_job.get_job_id()))
            self._run_queue.put(new_job)
            return detached_job

    def job_complete(self, job_id):
        if self._conf.jobs_retain_job_time == 0:
            return
        dcm_events.register_callback(self._job_cleanup,
                                     args=[job_id],
                                     delay=self._conf.jobs_retain_job_time)

    def _job_cleanup(self, job_id):
        with self._lock:
            _g_logger.debug("Removing job %d from the table" % job_id)
            del self._job_table[job_id]

    def lookup_job(self, job_id):
        with self._lock:
            try:
                return self._job_table[job_id]
            except Exception:
                return None

    def job_update_callback(self, job_reply):
        with self._lock:
            try:
                _g_logger.debug("long runner poll has the lock, "
                                "updating %s" % str(job_reply.job_id))

                jd = self._job_table[job_reply.job_id]
                if job_reply.error:
                    jd.update(job_reply, message=str(job_reply.error))
                else:
                    jd.update(job_reply)
                if jd._job_status == JobStatus.ERROR or\
                        jd._job_status == JobStatus.COMPLETE:
                    self.job_complete(job_reply.job_id)
            except Exception:
                _g_logger.exception("Failed to update")
                return None


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

    def update(self, work_reply, message=None):
        self._job_status = work_reply.job_status
        self._start_date = work_reply.start_date
        self._reply_doc = work_reply.reply_doc
        self._end_date = work_reply.end_date
        self._error = work_reply.error
        if message:
            self._message = urllib.parse.quote(message)
        if self._message is None and self._error is not None:
            self._message = urllib.parse.quote(str(self._error))

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
            "command_reply": self._reply_doc
        }
        return reply_object
