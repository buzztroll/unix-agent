import logging
import signal
import sys

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
from dcm.agent.messaging import handshake
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

    logger = logging.getLogger(__name__)

    # def get a connection object
    conn = config.get_connection_object(_g_conf_object)
    handshake_doc = handshake.get_handshake(_g_conf_object)
    conn.set_handshake(handshake_doc)
    handshake_reply = conn.connect()

    if handshake_reply["return_code"] != 200:
        raise Exception("handshake failed " + handshake_reply['error_message'])

    _g_conf_object.set_agent_id(handshake_doc["agent_id"])

    disp = dispatcher.Dispatcher(_g_conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(_g_conf_object, conn, disp)

    done = False
    while not done:
        try:
            if _g_shutting_down:
                # do it by checking the variable to avoid any threading
                # issues from the signal handler
                request_listener.shutdown()
            # service the connections that already exist
            done = request_listener.poll()
        except Exception as ex:
            # if we get a top level exception we allow the program to terminate
            # wrapper scripts can potentially make other decisions about
            # restarting it, but this is the python code saying we are finished
            # due to an unrecoverable error
            logger.error(ex)
            raise

    _g_conf_object.console_log(3, "Stopping the dispatcher.")
    disp.stop()
    conn.close()


def main(args=sys.argv):
    try:
        _run_agent(args)
    except exceptions.AgentOptionException as aoex:
        _g_conf_object.console_log(0, "The agent is misconfigured.")
        _g_conf_object.console_log(0, aoex.message)
    if _g_conf_object.get_cli_arg("verbose") > 2:
        raise


main()