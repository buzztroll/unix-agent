import logging
import os
import signal
import sys

import dcm.agent
from dcm.agent import utils
import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
from dcm.agent.messaging import handshake
import dcm.agent.messaging.reply as reply
from dcm.agent import parent_receive_q


_g_conf_object = config.AgentConfig()
_g_shutting_down = False


def kill_handler(signum, frame):
    shutdown_main_loop()


def shutdown_main_loop():
    global _g_shutting_down

    logger = logging.getLogger(__name__)

    logger.info("Shutting down.")
    _g_conf_object.console_log(0, "Shutting down.")
    _g_shutting_down = True
    parent_receive_q.wakeup()


def _pre_threads(conf, args):
    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)
    # def setup config object
    conf.setup(clioptions=True, args=args)

    if conf.pydev_host:
        utils.setup_remote_pydev(_g_conf_object.pydev_host,
                                 _g_conf_object.pydev_port)

    if 'PYDEVD_DEBUG_HOST' in os.environ:
        pydev = os.environ['PYDEVD_DEBUG_HOST']
        print pydev
        h, p = pydev.split(":")
        utils.setup_remote_pydev(h, int(p))


def _run_agent():
    _g_logger = logging.getLogger(__name__)

    # def get a connection object
    conn = config.get_connection_object(_g_conf_object)
    disp = dispatcher.Dispatcher(_g_conf_object)
    request_listener = reply.RequestListener(_g_conf_object, conn, disp)
    conn.set_receiver(request_listener)

    handshake_doc = handshake.get_handshake(_g_conf_object)
    conn.set_handshake(handshake_doc)
    handshake_reply = conn.connect()

    if handshake_reply["return_code"] != 200:
        raise Exception("handshake failed " + handshake_reply['message'])

    _g_conf_object.set_handshake(handshake_reply["initialize"])

    disp.start_workers(request_listener)

    rc = _agent_main_loop(_g_conf_object, request_listener, disp, conn)
    _cleanup_agent(_g_conf_object, request_listener, disp, conn)


def _agent_main_loop(conf, request_listener, disp, conn):
    logger = logging.getLogger(__name__)

    while not _g_shutting_down:
        try:
            parent_receive_q.poll()
        except:
            logger.exception("A top level exception occurred")


def _cleanup_agent(conf, request_listener, disp, conn):
    logger = logging.getLogger(__name__)

    logger.debug("Shutting down the job runner")
    conf.jr.shutdown()
    logger.debug("Stopping the reply listener")
    request_listener.shutdown()
    logger.debug("Stopping the dispatcher")
    disp.stop()
    logger.debug("Closing the connection")
    conn.close()
    logger.debug("Service closed")


def main(args=sys.argv):
    try:
        _pre_threads(_g_conf_object, args)
        if(_g_conf_object.get_cli_arg("version")):
            print "Version %s" % dcm.agent.g_version
            return 0
        _g_conf_object.start_job_runner()
        _run_agent()
    except exceptions.AgentOptionException as aoex:
        _g_conf_object.console_log(0, "The agent is misconfigured.")
        _g_conf_object.console_log(0, aoex.message)
        if _g_conf_object.get_cli_arg("verbose") > 2:
            raise
    except:
        _g_logger = logging.getLogger(__name__)
        _g_logger.exception("An unknown exception bubbled to the top")
        raise
    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
