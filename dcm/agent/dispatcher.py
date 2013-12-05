import logging
import Queue
import threading

import dcm.agent.jobs as jobs
import dcm.agent.messaging.utils as message_utils

# Threaded Object

class Worker(threading.Thread):
    logger = message_utils.MessageLogAdaptor(logging.getLogger(__name__), {})

    def __init__(self, worker_queue):
        threading.Thread.__init__(self)
        self.worker_queue = worker_queue
        self._done = False

    # It should be safe to call done without a lock
    def done(self):
        self.logger.debug("done() called on worker %s .." % self.getName())
        self._done = True


    def run(self):
        self.logger.info("Worker %s thread starting." % self.getName())

        # run until it is signaled as done and the worker queue is empty.
        # we have to wait for the worker queue to be empty because it is
        # possible that the get() will timeout, a new item will be placed
        # in the queue, and then done() will be called all before we get
        # to the top of the loop.
        # TODO add a force kill
        while not self._done or not self.worker_queue.empty():
            try:
                (reply, plugin) = self.worker_queue.get(True, 1)
                # setup message logging
                message_utils.setup_message_logging(reply.get_request_id(),
                                                    plugin.get_name())
                try:
                    self.logger.info("Starting job " + str(plugin))
                    (stdout, stderr, returncode) = plugin.run()
                    self.logger.info("Completed successfully job " + str(plugin))
                except Exception as ex:
                    self.logger.error("Worker %s thread had a top level error when "
                                      "running job %s" % (self.getName(), plugin), ex)
                    stdout = ""
                    stderr = ex.message
                    returncode = -1
                finally:
                    self.worker_queue.task_done()
                    self.logger.info("Task done job " + str(plugin))

                reply_message = {'stdout': stdout,
                                 'stderr': stderr,
                                 'returncode': returncode,
                                 "error": ""}

                # TODO XXX handle messaging errors
                reply.reply(reply_message)
            except Queue.Empty:
                self.logger.debug("Queue timeout")
            finally:
                message_utils.clear_message_logging()
        self.logger.info("Worker %s thread ending." % self.getName())


# TODO verify stopping behavior
class Dispatcher(object):

    logger = message_utils.MessageLogAdaptor(logging.getLogger(__name__), {})

    def __init__(self, conf):
        self.conf = conf
        self.workers = []
        self.worker_q = Queue.Queue()
        self._agent = None # figure out what we need here

    def start_workers(self):
        self.logger.info("Starting %d workers." % self.conf.workers_count)
        for i in range(self.conf.workers_count):
            worker = Worker(self.worker_q)
            self.logger.debug("Starting worker %d : %s" % (i, str(worker)))
            worker.start()
            self.workers.append(worker)

    def stop(self):
        self.logger.info("Stopping workers.")
        self.worker_q.join()
        for w in self.workers:
            self.logger.debug("Stopping worker %s" % str(w))
            w.done()
            w.join()
            self.logger.debug("Worker %s is done" % str(w))

    def incoming_request(self, reply, *args, **kwargs):
        try:
            payload = reply.get_message_payload()
            command_name = payload['command']
            arguments = payload['arguments']
            request_id = reply.get_request_id()
            self.logger.info("Creating a request ID %s" % request_id)
            plugin = jobs.load_plugin(
                self._agent, self.conf, request_id, command_name, arguments)

            message_utils.setup_message_logging(reply.get_request_id(),
                                                plugin.get_name())
            reply.lock()
            try:
                self.worker_q.put((reply, plugin))
                # there is an open window when the worker could pull the
                # command from the queue before it is acked.  The lock prevents
                # this
                reply.ack(plugin.cancel, None, None)
            finally:
                reply.unlock()
                message_utils.clear_message_logging()
        except:
            raise
