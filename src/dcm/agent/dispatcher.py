import logging
import queue
import threading
import urllib.error
import urllib.parse
import urllib.request

import dcm.agent.plugins.loader as plugin_loader
import dcm.agent.logger as dcm_logger
import dcm.agent.longrunners as longrunners
import dcm.eventlog.tracer as tracer

from dcm.agent.events.globals import global_space as dcm_events


_g_logger = logging.getLogger(__name__)


class WorkLoad(object):
    def __init__(self, request_id, payload, items_map):
        self.request_id = request_id
        self.payload = payload
        self.items_map = items_map
        self.quit = False


class WorkReply(object):
    def __init__(self, request_id, reply_doc):
        self.request_id = request_id
        self.reply_doc = reply_doc


def _run_plugin(conf, items_map, request_id, command, arguments):
    try:
        plugin = plugin_loader.load_plugin(
            conf,
            items_map,
            request_id,
            command,
            arguments)

        dcm_logger.log_to_dcm_console_job_started(job_name=command,
                                                  request_id=request_id)
        reply_doc = plugin.run()

        dcm_logger.log_to_dcm_console_job_succeeded(job_name=command,
                                                    request_id=request_id)
    except Exception as ex:
        _g_logger.exception(
            "Worker %s thread had a top level error when "
            "running job %s : %s"
            % (threading.current_thread().getName(), request_id, str(ex)))

        dcm_logger.log_to_dcm_console_job_failed(job_name=command,
                                                 request_id=request_id)
        reply_doc = {
            'Exception': urllib.parse.quote(str(ex).encode('utf-8')),
            'return_code': 1}
    finally:
        _g_logger.info("Task done job " + request_id)
    return reply_doc


class Worker(threading.Thread):

    def __init__(self, conf, worker_queue, reply_callback):
        super(Worker, self).__init__()
        self.worker_queue = worker_queue
        self._exit = threading.Event()
        self._conf = conf
        self._is_done = False
        self._reply_callback = reply_callback

    # It should be safe to call done without a lock
    def done(self):
        _g_logger.debug("done() called on worker %s .." % self.getName())
        self._is_done = True
        self._exit.set()

    def run(self):
        try:
            _g_logger.info("Worker %s thread starting." % self.getName())

            done = False
            while not done:
                try:
                    workload = self.worker_queue.get()
                    if workload is None:
                        continue
                    if workload.quit:
                        done = True
                        self.worker_queue.task_done()
                        continue

                    # setup message logging
                    with tracer.RequestTracer(workload.request_id):

                        reply_doc = _run_plugin(self._conf,
                                                workload.items_map,
                                                workload.request_id,
                                                workload.payload["command"],
                                                workload.payload["arguments"])
                        self.worker_queue.task_done()

                        _g_logger.debug(
                            "Adding the reply document to the reply "
                            "queue " + str(reply_doc))

                        work_reply = WorkReply(workload.request_id, reply_doc)
                        dcm_events.register_callback(
                            self._reply_callback, args=[work_reply])

                        _g_logger.info("Reply message sent for command " +
                                       workload.payload["command"])
                except queue.Empty:
                    pass
                except:
                    _g_logger.exception(
                        "Something went wrong processing the queue")
                    raise
        finally:
            _g_logger.info("Worker %s thread ending." % self.getName())


class Dispatcher(object):

    def __init__(self, conf):
        self._conf = conf
        self.workers = []
        self.worker_q = queue.Queue()
        self._long_runner = longrunners.LongRunner(conf)
        self.request_listener = None

    def start_workers(self, request_listener):
        _g_logger.info("Starting %d workers." % self._conf.workers_count)
        self.request_listener = request_listener
        for i in range(self._conf.workers_count):
            worker = Worker(self._conf, self.worker_q,
                            self.work_complete_callback)
            _g_logger.debug("Starting worker %d : %s" % (i, str(worker)))
            worker.start()
            self.workers.append(worker)

    def stop(self):
        _g_logger.info("Stopping workers.")

        for _ in self.workers:
            workload = WorkLoad(None, None, None)
            workload.quit = True
            self.worker_q.put(workload)

        for w in self.workers:
            _g_logger.debug("Stopping worker %s" % str(w))
            w.done()
            w.join()
            _g_logger.debug("Worker %s is done" % str(w))
        _g_logger.info("Shutting down the long runner.")
        self._long_runner.shutdown()
        _g_logger.info("Flushing the work queue.")
        while not self.worker_q.empty():
            self.worker_q.get()
        _g_logger.info("The dispatcher is closed.")

    def incoming_request(self, reply_obj):
        payload = reply_obj.get_message_payload()
        _g_logger.debug("Incoming request %s" % str(payload))
        request_id = reply_obj.get_request_id()
        _g_logger.info("Creating a request ID %s" % request_id)

        items_map = plugin_loader.parse_plugin_doc(
            self._conf, payload["command"])

        dcm_logger.log_to_dcm_console_incoming_message(
            job_name=payload["command"])

        immediate = "immediate" in items_map
        long_runner = "longer_runner" in items_map
        if "longer_runner" in payload:
            long_runner = bool(payload["longer_runner"])

        # we ack first.  This will write it to the persistent store before
        # sending the message so the agent will have it for restarts
        reply_obj.ack(None, None, None)
        if long_runner:
            try:
                dj = self._long_runner.start_new_job(
                    self._conf,
                    request_id,
                    items_map,
                    payload["command"],
                    payload["arguments"])
            except BaseException as ex:
                reply_doc = {
                    'Exception': urllib.parse.quote(str(ex).encode('utf-8')),
                    'return_code': 1}
            else:
                payload_doc = dj.get_message_payload()
                reply_doc = {
                    "return_code": 0,
                    "reply_type": "job_description",
                    "reply_object": payload_doc
                }
            wr = WorkReply(request_id, reply_doc)
            dcm_events.register_callback(
                self.work_complete_callback, args=[wr])
        elif immediate:
            items_map["long_runner"] = self._long_runner
            reply_doc = _run_plugin(self._conf,
                                    items_map,
                                    request_id,
                                    payload["command"],
                                    payload["arguments"])
            wr = WorkReply(request_id, reply_doc)
            dcm_events.register_callback(
                self.work_complete_callback, args=[wr])
        else:
            workload = WorkLoad(request_id, payload, items_map)
            self.worker_q.put(workload)

        _g_logger.debug(
            "The request %s has been set to send an ACK" % request_id)

    def work_complete_callback(self, work_reply):
        self.request_listener.reply(work_reply.request_id,
                                    work_reply.reply_doc)
