import logging
import Queue
import threading

import dcm.agent.jobs as jobs

# Threaded Object
from dcm.eventlog import tracer


_g_logger = logging.getLogger(__name__)


class Worker(threading.Thread):

    def __init__(self, worker_queue):
        threading.Thread.__init__(self)
        self.worker_queue = worker_queue
        self._done = False

    # It should be safe to call done without a lock
    def done(self):
        _g_logger.debug("done() called on worker %s .." % self.getName())
        self._done = True

    def run(self):
        _g_logger.info("Worker %s thread starting." % self.getName())

        while not self._done:
            try:
                (req_reply, plugin) = self.worker_queue.get(True, 1)
                # setup message logging
                with tracer.RequestTracer(req_reply.get_request_id()):
                    try:
                        _g_logger.info("Starting job " + str(plugin))
                        reply_doc = plugin.run()
                        _g_logger.info(
                            "Completed successfully job " + str(plugin))
                    except Exception as ex:
                        _g_logger.error(
                            "Worker %s thread had a top level error when "
                            "running job %s" % (self.getName(), plugin), ex)
                        reply_doc = {
                            'Exception': ex.message,
                            'return_code': 1}
                    finally:
                        self.worker_queue.task_done()
                        _g_logger.info("Task done job " + str(plugin))

                    _g_logger.debug("replying: " + str(reply_doc))

                    # TODO XXX handle messaging errors
                    req_reply.reply(reply_doc)
                    _g_logger.debug("Reply message sent")
            except Queue.Empty:
                pass
            except:
                _g_logger.exception(
                    "Something went wrong processing the queue")
        _g_logger.info("Worker %s thread ending." % self.getName())


# TODO verify stopping behavior
class Dispatcher(object):

    def __init__(self, conf):
        self.conf = conf
        self.workers = []
        self.worker_q = Queue.Queue()

    def start_workers(self):
        _g_logger.info("Starting %d workers." % self.conf.workers_count)
        for i in range(self.conf.workers_count):
            worker = Worker(self.worker_q)
            _g_logger.debug("Starting worker %d : %s" % (i, str(worker)))
            worker.start()
            self.workers.append(worker)

    def stop(self):
        _g_logger.info("Stopping workers.")
        self.worker_q.join()
        for w in self.workers:
            _g_logger.debug("Stopping worker %s" % str(w))
            w.done()
            w.join()
            _g_logger.debug("Worker %s is done" % str(w))
        _g_logger.info("The dispatcher is closed.")

    def incoming_request(self, reply, *args, **kwargs):
        payload = reply.get_message_payload()
        _g_logger.debug("Incoming request %s" % str(payload))
        command_name = payload['command']
        arguments = payload['arguments']
        request_id = reply.get_request_id()
        _g_logger.info("Creating a request ID %s" % request_id)

        plugin = jobs.load_plugin(
            self.conf, request_id, command_name, arguments)

        reply.lock()
        try:
            self.worker_q.put((reply, plugin))
            # there is an open window when the worker could pull the
            # command from the queue before it is acked.  The lock prevents
            # this
            reply.ack(plugin.cancel, None, None)
            _g_logger.debug(
                "The request %s has been set to send an ACK" % request_id)
        finally:
            reply.unlock()
