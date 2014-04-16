import argparse
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


_g_shutting_down = False
_g_conn_for_shutdown = None


def console_log(cli_args, level, msg, **kwargs):
    vb_level = getattr(cli_args, "verbose", 0)
    if level > vb_level:
        return
    print >> sys.stderr, msg % kwargs


def kill_handler(signum, frame):
    shutdown_main_loop()


def shutdown_main_loop():
    global _g_shutting_down

    if _g_conn_for_shutdown:
        _g_conn_for_shutdown.close()
    _g_shutting_down = True
    parent_receive_q.wakeup()


def _pre_threads(conf, args):
    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)
    # def setup config object

    if conf.pydev_host:
        utils.setup_remote_pydev(conf.pydev_host,
                                 conf.pydev_port)

    if 'PYDEVD_DEBUG_HOST' in os.environ:
        pydev = os.environ['PYDEVD_DEBUG_HOST']
        print pydev
        h, p = pydev.split(":")
        utils.setup_remote_pydev(h, int(p))


def _run_agent(conf):
    _g_logger = logging.getLogger(__name__)

    request_listener = None
    disp = None
    conn = None

    try:
        # def get a connection object
        global _g_conn_for_shutdown
        conn = config.get_connection_object(conf)
        disp = dispatcher.Dispatcher(conf)
        request_listener = reply.RequestListener(conf, conn, disp)
        conn.set_receiver(request_listener)

        handshake_doc = handshake.get_handshake(conf)
        if handshake_doc is None:
            raise Exception("A connection could not be made.")
        _g_logger.debug("Using handshake document %s" % str(handshake_doc))
        conn.set_handshake(handshake_doc)
        _g_conn_for_shutdown = conn
        handshake_reply = conn.connect()
        if handshake_reply is None:
            raise Exception("The agent was unable to connect to the agent manager")
        if handshake_reply["return_code"] != 200:
            raise Exception("handshake failed " + handshake_reply['message'])

        conf.set_handshake(handshake_reply["handshake"])

        disp.start_workers(request_listener)

        rc = _agent_main_loop(conf, request_listener, disp, conn)
    finally:
        _cleanup_agent(conf, request_listener, disp, conn)


def _agent_main_loop(conf, request_listener, disp, conn):
    logger = logging.getLogger(__name__)

    while not _g_shutting_down:
        try:
            parent_receive_q.poll()
        except:
            logger.exception("A top level exception occurred")


def _cleanup_agent(conf, request_listener, disp, conn):
    logger = logging.getLogger(__name__)

    if conf.jr:
        logger.debug("Shutting down the job runner")
        conf.jr.shutdown()
    if request_listener:
        logger.debug("Stopping the reply listener")
        request_listener.shutdown()
    if disp:
        logger.debug("Stopping the dispatcher")
        disp.stop()
    if conn:
        logger.debug("Closing the connection")
        conn.close()
    logger.debug("Service closed")


def parse_command_line(argv):
    conf_parser = argparse.ArgumentParser(description="Start the agent")
    conf_parser.add_argument(
        "-c", "--conffile", help="Specify config file", metavar="FILE",
        default=None)
    conf_parser.add_argument("-v", "--verbose", action="count",
                             help="Display more output on the console.",
                             default=0)
    conf_parser.add_argument("-V", "--version", action="store_true",
                             help="Display just the version of this "
                                  "agent installation.",
                             dest="version",
                             default=False)
    return conf_parser.parse_known_args(args=argv)


def main(args=sys.argv):
    try:
        cli_args, remaining_argv = parse_command_line(args)

        config_files = utils.get_config_files(conffile=cli_args.conffile)
        conf = config.AgentConfig(config_files)

        _pre_threads(conf, args)
        if cli_args.version:
            print "Version %s" % dcm.agent.g_version
            return 0
        utils.verify_config_file(conf)
        conf.start_job_runner()
        _run_agent(conf)
    except exceptions.AgentOptionException as aoex:
        console_log(cli_args, 0, "The agent is not configured properly. "
                                      "please check the config file.")
        console_log(cli_args, 0, aoex.message)
        shutdown_main_loop()
        if getattr(cli_args, "verbose", 0) > 2:
            raise
    except:
        _g_logger = logging.getLogger(__name__)
        console_log(
            cli_args,
            0, "Shutting down due to a top level exception")
        _g_logger.exception("An unknown exception bubbled to the top")
        shutdown_main_loop()
        raise
    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
