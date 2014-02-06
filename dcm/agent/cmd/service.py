import logging
import signal
import sys
from dcm.agent import utils

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
import dcm.agent.job_runner as job_runner
from dcm.agent.messaging import handshake
import dcm.agent.messaging.reply as reply


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


def _pre_threads(conf, args):
    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)
    # def setup config object
    conf.setup(clioptions=True, args=args)

    if conf.pydev_host:
        utils.setup_remote_pydev(_g_conf_object.pydev_host,
                                 _g_conf_object.pydev_port)

    conf.start_job_runner()


def _run_agent():
    _g_logger = logging.getLogger(__name__)

    # def get a connection object
    conn = config.get_connection_object(_g_conf_object)
    handshake_doc = handshake.get_handshake(_g_conf_object)
    conn.set_handshake(handshake_doc)
    handshake_reply = conn.connect()

    if handshake_reply["return_code"] != 200:
        raise Exception("handshake failed " + handshake_reply['message'])

    _g_conf_object.set_handshake(handshake_reply["initialize"])

    disp = dispatcher.Dispatcher(_g_conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(_g_conf_object, conn, disp)
    return _agent_main_loop(_g_conf_object, request_listener, disp, conn)


def _agent_main_loop(conf, request_listener, disp, conn):
    logger = logging.getLogger(__name__)

    while not _g_shutting_down:
        try:
            reply_obj = request_listener.poll()
            try:
                if reply_obj is not None:
                    disp.incoming_request(reply_obj)
                work_reply = disp.poll()
                if work_reply:
                    request_listener.reply(
                        work_reply.request_id, work_reply.reply_doc)
            except:
                logger.exception("A top level exception occurred after "
                                    "creating the request.  Cleaning up the "
                                    "request")
                reply_obj.shutdown()

        except:
            logger.exception("A top level exception occurred")

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
        _run_agent()
    except exceptions.AgentOptionException as aoex:
        _g_conf_object.agent_state = utils.AgentStates.STARTUP_ERROR
        _g_conf_object.console_log(0, "The agent is misconfigured.")
        _g_conf_object.console_log(0, aoex.message)
        if _g_conf_object.get_cli_arg("verbose") > 2:
            raise
    except:
        _g_logger = logging.getLogger(__name__)
        _g_logger.exception("An unknown exception bubbled to the top")
        raise
    finally:
        _g_logger.debug("Service closed")
    return 0

if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
