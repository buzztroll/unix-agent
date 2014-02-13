import logging
from dcm.agent import longrunners
import Queue
import threading

import dcm.agent.jobs as jobs
from dcm.eventlog import tracer


_g_logger = logging.getLogger(__name__)


class WorkLoad(object):
    def __init__(self, request_id, payload, items_map):
        self.request_id = request_id
        self.payload = payload
        self.items_map = items_map


class WorkReply(object):
    def __init__(self, request_id, reply_doc):
        self.request_id = request_id
        self.reply_doc = reply_doc


def _run_plugin(conf, items_map, request_id, command, arguments):
    try:
        plugin = jobs.load_plugin(
            conf,
            items_map,
            request_id,
            command,
            arguments)

        _g_logger.info("Starting job " + str(plugin))
        reply_doc = plugin.run()
        _g_logger.info(
            "Completed successfully job " + str(plugin))
    except Exception as ex:
        _g_logger.exception(
            "Worker %s thread had a top level error when "
            "running job %s : %s"
            % (threading.current_thread().getName(), request_id, ex.message))
        reply_doc = {
            'Exception': ex.message,
            'return_code': 1}
    finally:
        _g_logger.info("Task done job " + request_id)
    return reply_doc


class Worker(threading.Thread):

    def __init__(self, conf, worker_queue, reply_q):
        super(Worker, self).__init__()
        self.worker_queue = worker_queue
        self.reply_q = reply_q
        self._exit = threading.Event()
        self._conf = conf

    # It should be safe to call done without a lock
    def done(self):
        _g_logger.debug("done() called on worker %s .." % self.getName())
        self._exit.set()

    def run(self):
        _g_logger.info("Worker %s thread starting." % self.getName())

        while not self._exit.is_set():
            try:
                workload = self.worker_queue.get(True, 1)
                # setup message logging
                with tracer.RequestTracer(workload.request_id):

                    reply_doc = _run_plugin(self._conf,
                                            workload.items_map,
                                            workload.request_id,
                                            workload.payload["command"],
                                            workload.payload["arguments"])
                    self.worker_queue.task_done()

                    _g_logger.debug("Adding the reply document to the reply "
                                    "queue " + str(reply_doc))

                    work_reply = WorkReply(workload.request_id, reply_doc)
                    self.reply_q.put(work_reply)
                    _g_logger.debug("Reply message sent")
            except Queue.Empty:
                pass
            except:
                _g_logger.exception(
                    "Something went wrong processing the queue")
                raise

        _g_logger.info("Worker %s thread ending." %  self.getName())


# TODO verify stopping behavior
class Dispatcher(object):

    def __init__(self, conf):
        self._conf = conf
        self.workers = []
        self.worker_q = Queue.Queue()
        self.reply_q = Queue.Queue()
        self._long_runner = longrunners.LongRunner(conf)

    def start_workers(self):
        _g_logger.info("Starting %d workers." % self._conf.workers_count)
        for i in range(self._conf.workers_count):
            worker = Worker(self._conf, self.worker_q, self.reply_q)
            _g_logger.debug("Starting worker %d : %s" % (i, str(worker)))
            worker.start()
            self.workers.append(worker)

    def stop(self):
        _g_logger.info("Stopping workers.")
        for w in self.workers:
            _g_logger.debug("Stopping worker %s" % str(w))
            w.done()
            w.join()
            _g_logger.debug("Worker %s is done" % str(w))
        _g_logger.info("Shutting down the long runner.")
        self._long_runner.shutdown()
        _g_logger.info("Flushing the work queue.")
        while not self.worker_q.empty():
            workload = self.worker_q.get()
            #req_reply.shutdown()
        _g_logger.info("The dispatcher is closed.")

    def incoming_request(self, reply_obj):
        payload = reply_obj.get_message_payload()
        _g_logger.debug("Incoming request %s" % str(payload))
        request_id = reply_obj.get_request_id()
        _g_logger.info("Creating a request ID %s" % request_id)

        items_map = jobs.parse_plugin_doc(self._conf, payload["command"])

        if "longer_runner" in items_map:
            dj = self._long_runner.start_new_job(
                    self._conf,
                    request_id,
                    items_map,
                    payload["command"],
                    payload["arguments"])
            payload_doc = dj.get_message_payload()
            reply_doc = {
                "return_code": 0,
                "reply_type": "job_description",
                "reply_object": payload_doc
            }
            wr = WorkReply(request_id, reply_doc)
            self.reply_q.put(wr)
        elif "immediate" in items_map:
            items_map["long_runner"] = self._long_runner
            reply_doc = _run_plugin(self._conf,
                                    items_map,
                                    request_id,
                                    payload["command"],
                                    payload["arguments"])
            wr = WorkReply(request_id, reply_doc)
            self.reply_q.put(wr)
        else:
            workload = WorkLoad(request_id, payload, items_map)
            self.worker_q.put(workload)

        # there is an open window when the worker could pull the
        # command from the queue before it is acked.  A lock could
        # prevent this but it is safe so long as poll and incoming_request
        # are called in the same thread
        reply_obj.ack(None, None, None)
        _g_logger.debug(
            "The request %s has been set to send an ACK" % request_id)

    def poll(self):
        rc = None
        try:
            work_reply = self.reply_q.get(True, 1)
            rc = work_reply
        except Queue.Empty:
            pass
        self._long_runner.poll()
        return rc
