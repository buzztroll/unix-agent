import logging
import signal
import sys

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
import dcm.agent.messaging.utils as utils
import dcm.agent.messaging.reply as reply

_g_conf_object = config.AgentConfig()
_g_shutting_down = False


def kill_handler(signum, frame):
    global _g_shutting_down
    _g_conf_object.console_log(0, "Shutting down.")
    _g_shutting_down = True


def _run_agent(args):
    global _g_shutting_down

    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)
    # def setup config object
    _g_conf_object.setup(clioptions=True)

    logger = utils.MessageLogAdaptor(logging.getLogger(__name__), {})

    # def get a connection object
    conn = config.get_connection_object(_g_conf_object)

    disp = dispatcher.Dispatcher(_g_conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(
        conn, disp, timeout=_g_conf_object.messaging_retransmission_timeout)

    # TODO drive this loop with something real
    done = False
    while not done:
        try:
            if _g_shutting_down:
                request_listener.shutdown()
            # service the connections that already exist
            done = request_listener.poll()
        except Exception as ex:
            logger.error(ex)
            raise

    _g_conf_object.console_log(3, "Stopping the dispatcher.")
    disp.stop()


def main(args=sys.argv):
    try:
        _run_agent(args)
    except exceptions.AgentOptionException as aoex:
        _g_conf_object.console_log(0, "The agent is misconfigured.")
        _g_conf_object.console_log(0, aoex.message)
    if _g_conf_object.get_cli_arg("verbose") > 2:
        raise
