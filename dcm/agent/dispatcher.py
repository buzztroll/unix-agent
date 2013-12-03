import logging
import Queue
import threading
import uuid

import dcm.agent.jobs as jobs
import dcm.agent.exceptions as exceptions


class Worker(threading.Thread):
    logger = logging.getLogger(__name__)

    def __init__(self, worker_queue):
        threading.Thread.__init__(self)
        self.worker_queue = worker_queue
        self.done = False

    # It should be safe to call done without a lock
    def done(self):
        self.done = True

    def run(self):
        self.logger.info("Worker %s thread starting." % self.getName())
        while not self.done:
            (reply, plugin) = self.worker_queue.get()
            try:
                self.logger.info("Starting job " + str(plugin))
                plugin.run()
                self.logger.info("Completed successfully job " + str(plugin))
            except Exception as ex:
                self.logger.error("Worker %s thread had a top level error when "
                                  "running job %s" % (self.getName(), plugin), ex)
            finally:
                self.worker_queue.task_done()
                self.logger.info("Task done job " + str(plugin))
        self.logger.info("Worker %s thread ending." % self.getName())


# TODO verify stopping behavior
class Dispatcher(object):

    logger = logging.getLogger(__name__)

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
            job_id = str(uuid.uuid4())
            self.logger.info("Creating a job ID %s" % job_id)
            plugin = jobs.load_plugin(
                self._agent, self.conf, job_id, command_name, arguments)
            self.worker_q.put((reply, plugin))
            # there is an open window when the worker could pull the
            # command from the queue before it is acked.  this should
            # be made safe by the reply state machine
            # TODO have state machine handle ack after reply
            # TODO trap any invalid states
            reply.ack(plugin.cancel, None, None)
        except:
            raise
