import logging
import signal
import sys
from dcm.agent import utils

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
from dcm.agent.messaging import handshake
import dcm.agent.messaging.reply as reply


_g_conf_object = config.AgentConfig()
_g_shutting_down = False


def kill_handler(signum, frame):
    global _g_shutting_down

    logger = logging.getLogger(__name__)

    logger.info("Shutting down.")
    _g_conf_object.console_log(0, "Shutting down.")
    _g_shutting_down = True


def _run_agent(args):
    global _g_shutting_down

    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)
    # def setup config object
    _g_conf_object.setup(clioptions=True)

    _g_logger = logging.getLogger(__name__)

    if _g_conf_object.pydev_host:
        utils.setup_remote_pydev(_g_conf_object.pydev_host,
                                 _g_conf_object.pydev_port)

    # def get a connection object
    conn = config.get_connection_object(_g_conf_object)
    handshake_doc = handshake.get_handshake(_g_conf_object)
    conn.set_handshake(handshake_doc)
    handshake_reply = conn.connect()

    if handshake_reply["return_code"] != 200:
        raise Exception("handshake failed " + handshake_reply['error_message'])

    _g_conf_object.set_agent_id(handshake_reply["agent_id"])
    disp = dispatcher.Dispatcher(_g_conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(_g_conf_object, conn, disp)

    while not _g_shutting_down:
        try:
            request_listener.poll()
        except:
            _g_logger.exception("WHAT IS HAPPENING")

    _g_logger.debug("Stopping the reply listener")
    request_listener.shutdown()
    _g_logger.debug("Stopping the dispatcher")
    disp.stop()
    _g_logger.debug("Closing the connection")
    conn.close()
    _g_logger.debug("Service closed")


def main(args=sys.argv):
    try:
        _run_agent(args)
    except exceptions.AgentOptionException as aoex:
        _g_conf_object.console_log(0, "The agent is misconfigured.")
        _g_conf_object.console_log(0, aoex.message)
        if _g_conf_object.get_cli_arg("verbose") > 2:
            raise
    except:
        _g_logger = logging.getLogger(__name__)
        _g_logger.exception("An unknown exception bubbled to the top")
    finally:
            _g_logger.debug("Service closed")

main()
