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

    _g_conf_object.start_job_runner()

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
                _g_logger.exception("A top level exception occurred after "
                                    "creating the request.  Cleaning up the "
                                    "request")
                reply_obj.shutdown()

        except:
            _g_logger.exception("A top level exception occurred")

    _g_logger.debug("Shutting down the job runner")
    _g_conf_object.jr.shutdown()
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
