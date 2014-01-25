import logging
import Queue
import threading
import time
from dcm.agent import exceptions

import dcm.agent.jobs as jobs
import dcm.agent.messaging.utils as message_utils

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

        # run until it is signaled as done and the worker queue is empty.
        # we have to wait for the worker queue to be empty because it is
        # possible that the get() will timeout, a new item will be placed
        # in the queue, and then done() will be called all before we get
        # to the top of the loop.
        # TODO add a force kill
        while not self._done:
            try:
                (reply, plugin) = self.worker_queue.get(True, 1)
                # setup message logging
                with tracer.RequestTracer(reply.get_request_id()):
                    try:
                        _g_logger.info("Starting job " + str(plugin))
                        reply_doc = plugin.run()
                        _g_logger.info(
                            "Completed successfully job " + str(plugin))
                    except Exception as ex:
                        _g_logger.error(
                            "Worker %s thread had a top level error when "
                            "running job %s" % (self.getName(), plugin), ex)
                        reply_doc = {'Exception': ex.message}
                    finally:
                        self.worker_queue.task_done()
                        _g_logger.info("Task done job " + str(plugin))

                    _g_logger.debug("replying: " + str(reply_doc))

                    # TODO XXX handle messaging errors
                    reply.reply(reply_doc)
                    _g_logger.debug("Reply message sent")
            except Queue.Empty:
                pass
            except:
                _g_logger.exception("Something went wrong processing the queue")
        _g_logger.info("Worker %s thread ending." % self.getName())


# TODO verify stopping behavior
class Dispatcher(object):

    def __init__(self, conf):
        self.conf = conf
        self.workers = []
        self.worker_q = Queue.Queue()
        self._agent = None  # figure out what we need here

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

        try:
            plugin = jobs.load_plugin(
                self._agent, self.conf, request_id, command_name, arguments)
        except Exception as ex:
            _g_logger.error("EEERRRROR", ex)
            time.sleep(5)
            raise

        _g_logger.info("Pre disp lock")

        reply.lock()
        try:
            _g_logger.info("have lock")
            self.worker_q.put((reply, plugin))
            # there is an open window when the worker could pull the
            # command from the queue before it is acked.  The lock prevents
            # this
            reply.ack(plugin.cancel, None, None)
            _g_logger.info("acked")
        finally:
            reply.unlock()
        _g_logger.info("un lock")


