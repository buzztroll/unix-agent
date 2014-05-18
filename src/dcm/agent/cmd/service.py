import argparse
import logging
import os
import signal
import sys

import dcm.agent
import dcm.agent.am_sender as am_sender
import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
import dcm.agent.logger as logger
import dcm.agent.messaging.handshake as handshake
import dcm.agent.messaging.reply as reply
import dcm.agent.parent_receive_q as parent_receive_q
import dcm.agent.utils as utils


_g_conf_file_env = "DCM_AGENT_CONF"


def get_config_files(base_dir=None, conffile=None):
    candidates = ["/etc/dcm/agent.conf",
                  os.path.expanduser("~/.dcm/agent.conf")]
    if base_dir:
        candidates.append(os.path.join(base_dir, "etc", "agent.conf"))
    if _g_conf_file_env in os.environ:
        candidates.append(os.environ[_g_conf_file_env])
    if conffile:
        candidates.append(conffile)

    locations = []
    for f in candidates:
        f = os.path.abspath(f)
        if os.path.exists(f):
            locations.append(f)
        else:
            logging.warn("Config file locations %s does not exist" % f)

    return locations


class DCMAgent(object):

    def __init__(self, conf):
        self.shutting_down = False
        self.conn = None
        self.conf = conf
        self.disp = None
        self.request_listener = None
        self.incoming_handshake_doc = None
        self.g_logger = logging.getLogger(__name__)

    def kill_handler(self, signum, frame):
        self.shutdown_main_loop()

    def stack_trace_handler(self, signum, frame):
        utils.build_assertion_exception(self.g_logger, "signal stack")

    def shutdown_main_loop(self):
        self.shutting_down = True
        parent_receive_q.wakeup()

    def pre_threads(self):
        signal.signal(signal.SIGINT, self.kill_handler)
        signal.signal(signal.SIGTERM, self.kill_handler)
        signal.signal(signal.SIGUSR2, self.stack_trace_handler)

        if self.conf.pydev_host:
            utils.setup_remote_pydev(self.conf.pydev_host,
                                     self.conf.pydev_port)

        if 'PYDEVD_DEBUG_HOST' in os.environ:
            pydev = os.environ['PYDEVD_DEBUG_HOST']
            h, p = pydev.split(":")
            utils.setup_remote_pydev(h, int(p))

    def run_agent(self):
        try:
            # def get a connection object
            self.conn = config.get_connection_object(self.conf)
            self.disp = dispatcher.Dispatcher(self.conf)
            self.request_listener = \
                reply.RequestListener(self.conf, self.conn, self.disp)

            handshake_doc = handshake.get_handshake(self.conf)
            self.g_logger.debug("Using outgoing handshake document %s"
                                % str(handshake_doc))
            logger.set_dcm_connection(self.conn)
            self.conn.connect(
                self.request_listener, self.incoming_handshake, handshake_doc)

            rc = self.agent_main_loop()
            return rc
        finally:
            self.cleanup_agent()

    def incoming_handshake(self, incoming_handshake_doc):
        self.g_logger.info("Incoming handshake %s" % str(incoming_handshake_doc))
        if self.incoming_handshake_doc is not None:
            # we already received a handshake, just return
            return True

        self.incoming_handshake_doc = incoming_handshake_doc
        if incoming_handshake_doc["return_code"] != 200:
            return False

        self.conf.set_handshake(incoming_handshake_doc["handshake"])
        utils.log_to_dcm(
            logging.INFO, "A handshake was successful, starting the workers")
        self.disp.start_workers(self.request_listener)

        return True

    def agent_main_loop(self):
        while not self.shutting_down:
            try:
                parent_receive_q.poll()
            except Exception as ex:
                utils.log_to_dcm(
                    logging.ERROR, "A top level exception occurred: %s" % ex.message)
                self.g_logger.exception("A top level exception occurred")

    def cleanup_agent(self):
        if self.conf.jr:
            self.g_logger.debug("Shutting down the job runner")
            self.conf.jr.shutdown()
        if self.request_listener:
            self.g_logger.debug("Stopping the reply listener")
            self.request_listener.shutdown()
        if self.disp:
            self.g_logger.debug("Stopping the dispatcher")
            self.disp.stop()
        if self.conn:
            self.g_logger.debug("Closing the connection")
            self.conn.close()
        self.g_logger.debug("Service closed")


def console_log(cli_args, level, msg, **kwargs):
    vb_level = getattr(cli_args, "verbose", 0)
    if level > vb_level:
        return
    print >> sys.stderr, msg % kwargs


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
    agent = None
    cli_args, remaining_argv = parse_command_line(args)
    try:

        config_files = get_config_files(conffile=cli_args.conffile)
        conf = config.AgentConfig(config_files)

        agent = DCMAgent(conf)
        agent.pre_threads()
        if cli_args.version:
            print "Version %s" % dcm.agent.g_version
            return 0

        utils.verify_config_file(conf)
        conf.start_job_runner()
        agent.run_agent()
    except exceptions.AgentOptionException as aoex:
        console_log(cli_args, 0, "The agent is not configured properly. "
                    "please check the config file.")
        console_log(cli_args, 0, aoex.message)
        if agent:
            agent.shutdown_main_loop()
        if getattr(cli_args, "verbose", 0) > 2:
            raise
    except:
        _g_logger = logging.getLogger(__name__)
        console_log(
            cli_args,
            0, "Shutting down due to a top level exception")
        _g_logger.exception("An unknown exception bubbled to the top")
        if agent:
            agent.shutdown_main_loop()
        raise
    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
