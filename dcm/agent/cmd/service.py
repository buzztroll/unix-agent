import logging
import signal
import sys

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
import dcm.agent.messaging.utils as utils
import dcm.agent.messaging.reply as reply

_shutting_down = False

def kill_handler(signum, frame):
    global _shutting_down
    print >> sys.stderr, "Shutdown..."
    _shutting_down = True


def _run_agent(args):

    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)
    # def setup config object
    conf_object = config.AgentConfig()
    conf_object.setup(clioptions=True)

    logger = utils.MessageLogAdaptor(logging.getLogger(__name__), {})

    # def get a connection object
    conn = config.get_connection_object(conf_object)

    disp = dispatcher.Dispatcher(conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(
        conn, disp, timeout=conf_object.messaging_retransmission_timeout)

    # TODO drive this loop with something real
    done = False
    while not done:
        try:
            if _shutting_down:
                request_listener.shutdown()
            # service the connections that already exist
            done = request_listener.poll()
        except Exception as ex:
            logger.error(ex)
            raise

    disp.stop()


def main(args=sys.argv):
    try:
        _run_agent(args)
    except exceptions.AgentOptionException as aoex:
        print >> sys.stderr, "The agent is misconfigured."
        print >> sys.stderr, aoex.message
