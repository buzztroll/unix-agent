import json
import datetime
import argparse
import logging
import os
import signal
import sys
import clint
import psutil

import dcm.agent
import dcm.agent.messaging as messaging
import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.exceptions as exceptions
import dcm.agent.logger as logger
from dcm.agent.messaging import persistence
import dcm.agent.handshake as handshake
import dcm.agent.messaging.reply as reply
import dcm.agent.parent_receive_q as parent_receive_q
import dcm.agent.utils as utils
import dcm.agent.intrusion_detection as intrusion_detect
import dcm.agent.cloudmetadata as cm

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
        self.g_logger.info("Using DB %s" % conf.storage_dbfile)
        self._db = persistence.FakeAgentDB(conf.storage_dbfile)
        self._intrusion_detection = None
        self.db_cleaner = None

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
            self.db_cleaner = persistence.DBCleaner(
                self._db, self.conf.storage_db_timeout, 100000, 3600)
            self.db_cleaner.start()

            # def get a connection object
            self.conn = config.get_connection_object(self.conf)
            self.disp = dispatcher.Dispatcher(self.conf)
            self.request_listener = reply.RequestListener(
                self.conf, self.conn, self.disp, self._db)

            self._intrusion_detection = \
                intrusion_detect.setup_intrusion_detection(
                    self.conf, self.conn)
            if self._intrusion_detection:
                self._intrusion_detection.start()
            self.conf.page_monitor.start()

            handshake_doc = handshake.get_handshake(self.conf)
            self.g_logger.debug("Using outgoing handshake document %s"
                                % str(handshake_doc))
            logger.set_dcm_connection(self.conf, self.conn)
            self.conn.connect(
                self.request_listener, self.incoming_handshake, handshake_doc)

            rc = self.agent_main_loop()
            return rc
        finally:
            self.cleanup_agent()

    def incoming_handshake(self, incoming_handshake_doc):
        self.g_logger.info(
            "Incoming handshake %s" % str(incoming_handshake_doc))
        if self.incoming_handshake_doc is not None:
            # we already received a handshake, just return
            return True

        self.incoming_handshake_doc = incoming_handshake_doc
        if incoming_handshake_doc["return_code"] != 200:
            return False

        self.conf.set_handshake(incoming_handshake_doc["handshake"])
        # clean the db if the agent_id doesnt match it
        utils.log_to_dcm(
            logging.INFO, "Clean up any bad residue in the db")
        self._db.check_agent_id(self.conf.agent_id)
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
                    logging.ERROR,
                    "A top level exception occurred: %s" % ex.message)
                self.g_logger.exception("A top level exception occurred")

    def cleanup_agent(self):
        parent_receive_q.flush()
        if self.db_cleaner:
            self.g_logger.debug("Shutting down the db cleaner runner")
            self.db_cleaner.done()
            self.db_cleaner.join()
        if self._intrusion_detection:
            self._intrusion_detection.stop()
        self.g_logger.debug("Shutting down the job runner")
        self.conf.stop_job_runner()
        if self.request_listener:
            self.g_logger.debug("Stopping the reply listener")
            self.request_listener.shutdown()
        if self.disp:
            self.g_logger.debug("Stopping the dispatcher")
            self.disp.stop()
        if self.conn:
            self.g_logger.debug("Closing the connection")
            self.conn.close()

        self.g_logger.debug("Stopping the pager service")
        self.conf.page_monitor.stop()
        self.g_logger.debug("Service closed")


def console_log(cli_args, level, msg, **kwargs):
    vb_level = getattr(cli_args, "verbose", 0)
    if level > vb_level:
        return
    print >> sys.stderr, msg % kwargs


def _get_info(conf):
    if os.path.isfile("/tmp/boot.log"):
        with open("/tmp/boot.log", "r") as mfile:
            boot_data = mfile.read()
    if os.path.isfile("/tmp/error.log"):
        with open("/tmp/error.log", "r") as mfile:
            error_data = mfile.read()
    effective_cloud = cm.guess_effective_cloud(conf)
    meta_data_obj = conf.meta_data_object
    platform = utils.identify_platform(conf)
    version = dcm.agent.g_version
    print "Effective cloud is: " + effective_cloud
    print "MetaData object is: " + str(meta_data_obj)
    print "Platform is %s %s" % (platform[0], platform[1])
    print "Version: " + version
    print "*************************log files*********************************"
    print boot_data if boot_data else "no boot data"
    print error_data if error_data else "no error data"
    print "**********************end log files*********************************"


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
    conf_parser.add_argument("-r", "--report", action="store_true",
                             help="Get debug info on agent installation.",
                             dest="report",
                             default=False)
    return conf_parser.parse_known_args(args=argv)


def start_main_service(cli_args):
    agent = None
    try:
        config_files = get_config_files(conffile=cli_args.conffile)
        conf = config.AgentConfig(config_files)

        agent = DCMAgent(conf)
        agent.pre_threads()
        if cli_args.version:
            print "Version %s" % dcm.agent.g_version
            return 0

        if cli_args.report:
            utils._g_logger.disabled = True
            cm._g_logger.disabled = True
            config._g_logger.disabled = True
            agent.g_logger.disabled = True
            _get_info(conf)
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


def get_status(cli_args):
    config_files = get_config_files(conffile=cli_args.conffile)
    conf = config.AgentConfig(config_files)

    db_obj = messaging.persistence.FakeAgentDB(conf.storage_dbfile)

    complete = db_obj.get_all_complete()
    replied = db_obj.get_all_reply()
    rejected = db_obj.get_all_rejected()
    acked = db_obj.get_all_ack()
    reply_nacked = db_obj.get_all_reply_nacked()
    status = "UNKNOWN"
    color_func = clint.textui.colored.yellow

    def _check_command(cmd):
        try:
            payload_doc = request_doc['payload']
            command = payload_doc['command']
            if command == cmd:
                return True
        except:
            pass
        return False

    for r in complete:
        request_doc = json.loads(r.request_doc)
        if _check_command("initialize"):
            status = "INITIALIZED"
            color_func = clint.textui.colored.green
    for r in acked:
        request_doc = json.loads(r.request_doc)
        if _check_command("initialize"):
            status = "INITIALIZING"
            color_func = clint.textui.colored.green
    for r in replied:
        request_doc = json.loads(r.request_doc)
        if _check_command("initialize"):
            status = "INITIALIZING"
            color_func = clint.textui.colored.green
    for r in reply_nacked:
        request_doc = json.loads(r.request_doc)
        if _check_command("initialize"):
            status = "UNKNOWN INITIALIZATION STATE"
            color_func = clint.textui.colored.red

    for r in rejected:
        request_doc = json.loads(r.request_doc)
        if _check_command("initialize"):
            status = "INITIALIZATION REJECTED"
            color_func = clint.textui.colored.red

    clint.textui.puts(color_func(status))
    complete = db_obj.get_all_complete()
    replied = db_obj.get_all_reply()
    rejected = db_obj.get_all_rejected()
    acked = db_obj.get_all_ack()
    reply_nacked = db_obj.get_all_reply_nacked()

    label_col_width = 30
    vals = [(complete, "Commands processed: "),
            (rejected, "Commands rejected: "),
            (acked, "Commands being processed: "),
            (replied, "Commands being replying to: "),
            (reply_nacked, "Replies rejected: ")]
    with clint.textui.indent(4):
        for v, k in vals:
            clint.textui.puts(
                clint.textui.columns([k, label_col_width], [str(len(v)), 5]))

    try:
        pid_file = os.path.join(conf.storage_base_dir, "dcm-agent.pid")
        if not os.path.exists(pid_file):
            run_status = "NOT RUNNING"
            run_reason = "PID file not found"
        else:
            with open(pid_file, "r") as fptr:
                pid = int(fptr.read().strip())
            p = psutil.Process(pid)
            clint.textui.puts(clint.textui.colored.green("RUNNING"))
            start_time_str = datetime.datetime.fromtimestamp(
                p.create_time).strftime("%Y-%m-%d %H:%M:%S")
            with clint.textui.indent(4):
                clint.textui.puts(clint.textui.columns(
                    ["Started at:", label_col_width],
                    [start_time_str, 70 - label_col_width]))
                clint.textui.puts(clint.textui.columns(
                    ["User:", label_col_width],
                    [p.username, 70 - label_col_width]))
                clint.textui.puts(clint.textui.columns(
                    ["Status:", label_col_width],
                    [p.status, 70 - label_col_width]))
                clint.textui.puts(clint.textui.columns(
                    ["Pid:", label_col_width],
                    [str(pid), 70 - label_col_width]))

            return 0
    except psutil.NoSuchProcess:
        run_status = "NOT RUNNING"
        run_reason = "The PID %d was not found" % pid
    except Exception as ex:
        run_reason = ex.message
        run_status = "UNKNOWN"

    clint.textui.puts(clint.textui.colored.red(run_status))
    clint.textui.puts(clint.textui.colored.red(run_reason))

    return 1


def main(args=sys.argv):
    cli_args, remaining_argv = parse_command_line(args)

    if remaining_argv and len(remaining_argv) > 1 and \
            remaining_argv[1].lower() == "status":
        # do status reporting
        return get_status(cli_args)
    else:
        # start main service
        return start_main_service(cli_args)

if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
