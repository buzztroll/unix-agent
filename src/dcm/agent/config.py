import argparse
import ConfigParser
import logging
import logging.config
import os
import sys
import tempfile
import yaml
import dcm
from dcm.agent import job_runner
from dcm.agent.cloudmetadata import CLOUD_TYPES
from dcm.agent.connection import websocket

import dcm.agent.exceptions as exceptions
import dcm.agent.connection.dummy as dummy_con
import dcm.agent.tests.utils.test_connection as test_connection


_g_logger = logging.getLogger(__name__)
_g_conf_file_env = "DCM_AGENT_CONF"


class AgentToken(object):
    def __init__(self, encrypted_token, date_string):
        self.encrypted_token = encrypted_token
        self.date_string = date_string


def get_connection_object(conf):
    con_type = conf.connection_type
    if not con_type:
        raise exceptions.AgentOptionValueNotSetException("connection_type")

    # XXX should we stevedore load this or __import__ it or go with a
    # hard coded list?  for now hard coded list

    if con_type == "success_tester":
        source_file = conf.connection_source_file
        if not source_file:
            raise exceptions.AgentOptionValueNotSetException(
                "[connection]source_file",
                msg="Using the %s connection type." % con_type)
        fptr = open(source_file, "r")
        if not conf.connection_dest_file:
            raise exceptions.AgentOptionValueNotSetException(
                "[connection]dest_file",
                msg="Using the %s connection type." % con_type)

        outf = open(conf.connection_dest_file, "w")
        con = test_connection.TestReplySuccessfullyAlways(fptr, outf)
    elif con_type == "dummy":
        con = dummy_con.DummyConnection()
    elif con_type == "ws":
        con = websocket.WebSocketConnection(conf.enstratius_agentmanager_url)
    else:
        raise Exception("Unknown connection type")
    return con


class ConfigOpt(object):

    def __init__(self, section, name, t, default=None,
                 options=None, minv=None, maxv=None, help=None):
        self.section = section
        self.name = name
        self.my_type = t
        self.options = options
        self.default = default
        self.minv = minv
        self.maxv = maxv
        self.help = help

    def get_option_name(self):
        option_name = "%s_%s" % (self.section, self.name)
        return option_name

    def get_default(self):
        return self.default

    def get_help(self):
        return self.help

    def get_value(self, parser, default=None, **kwargs):
        if default is None:
            default = self.default
        try:
            v = parser.get(self.section, self.name, default)
        except ConfigParser.NoOptionError:
            v = default
        except ConfigParser.NoSectionError:
            v = default
        if v is None:
            return v
        try:
            if self.my_type == list:
                v = v.split(",")
            else:
                v = self.my_type(v)
        except ValueError:
            raise exceptions.AgentOptionTypeException(
                self.name, self.my_type, v)

        if self.options is not None:
            vx = v
            if type(v) == str:
                vx = vx.lower()
                if vx not in self.options:
                    raise exceptions.AgentOptionValueException(
                        self.name, self.options, self.v)

        if self.my_type == int or self.my_type == float:
            if self.minv is not None and v < self.minv:
                raise exceptions.AgentOptionRangeException(
                    self.name, self.minv, self.maxv)
            if self.maxv is not None and v > self.maxv:
                raise exceptions.AgentOptionValueException(
                    self.name, self.minv, self.maxv)

        return v


class FilenameOpt(ConfigOpt):

    def __init__(self, section, name, default=None, help=None):
        super(FilenameOpt, self).__init__(section, name, str, default=default,
                                          help=help)

    def get_value(self, parser, relative_path=None, **kwarg):
        v = super(FilenameOpt, self).get_value(parser)
        if v is None:
            return None
        if not os.path.isabs(v):
            v = os.path.join(relative_path, v)
        return os.path.abspath(v)


class AgentConfig(object):
    top_logger = 'dcm.agent'

    def __init__(self):
        self._cli_args = None
        self._remaining_argv = None
        self._agent_id = None
        self.instance_id = None
        self._init_file_options()

    def _init_file_options(self):
        self.option_list = [
            ConfigOpt("pydev", "host", str, default=None, options=None,
                      help="The hostname of the pydev debugger"),
            ConfigOpt("pydev", "port", int, default=None, options=None,
                      help="The port where the pydev debugger is listening"),

            ConfigOpt("workers", "count", int, default=4, options=None,
                      help="The number of worker threads that will be "
                           "processing incoming requests"),

            ConfigOpt("workers", "long_runner_threads", int, default=1,
                      options=None,
                      help="The number of worker threads that will be "
                           "processing long running jobs (anything that "
                           "returns a job description)"),

            ConfigOpt("connection", "type", str, default=None, options=None,
                      help="The type of connection object to use.  Supported "
                           "types are ws and fallback"),

            ConfigOpt("connection", "hostname", str, default=None),
            FilenameOpt("connection", "source_file", default=None),
            FilenameOpt("connection", "dest_file", default=None),
            ConfigOpt("connection", "port", int, default=5309, options=None),

            FilenameOpt("logging", "configfile", default=None,
                        help ="The location of the log configuration file"),

            FilenameOpt("plugin", "configfile",
                        help="The location of the plugin configuration file"),

            FilenameOpt("storage", "temppath", default="/tmp"),
            FilenameOpt("storage", "services_dir", default="/mnt/services"),
            FilenameOpt("storage", "base_dir", default="/dcm"),
            FilenameOpt("storage", "binaries_path", default="/dcm/bin"),
            FilenameOpt("storage", "ephemeral_mountpoint", default="/mnt"),
            FilenameOpt("storage", "operations_path", default="/mnt"),
            FilenameOpt("storage", "idfile", default=None),

            ConfigOpt("cloud", "name", str, default=None),
            ConfigOpt("cloud", "type", str, default=CLOUD_TYPES.Amazon),
            ConfigOpt("cloud", "metadata_url", str,
                      default="http://169.254.169.254/1.0/meta-data"),

            ConfigOpt("messaging", "retransmission_timeout", float,
                      default=5),
            ConfigOpt("messaging", "max_at_once", int, default=-1),

            ConfigOpt("enstratius", "agentmanager_url", str, default=None),
            ConfigOpt("platform", "script_locations", list,
                      default="common-linux"),
            ConfigOpt("platform", "name", str, default="python"),
            ConfigOpt("jobs", "retain_job_time", int, default=3600),
        ]
        for o in self.option_list:
            k = o.get_option_name()
            v = o.get_default()
            self.__setattr__(k, v)

    def _parse_command_line(self, argv):
        conf_parser = argparse.ArgumentParser(
            description="Start the agent")
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
        self._cli_args, self._remaining_argv = \
            conf_parser.parse_known_args(args=argv)

    def get_cli_arg(self, key):
        return getattr(self._cli_args, key, None)

    def _parse_config_file(self, config_file):

        relative_path = os.path.dirname(config_file)

        parser = ConfigParser.SafeConfigParser()
        parser.read(config_file)

        for opt in self.option_list:
            try:
                oname = opt.get_option_name()
                v = opt.get_value(parser, relative_path=relative_path,
                                  default=getattr(self, oname))
                self.__setattr__(oname, v)
            except ConfigParser.NoSectionError as nse:
                opt.get
                raise exceptions.AgentOptionSectionNotFoundException(
                    opt.name)

    def _setup_logging(self):
        if self.logging_configfile is None:
            loghandler = logging.StreamHandler()
            top_logger = logging.getLogger("")
            top_logger.setLevel(logging.DEBUG)
            top_logger.addHandler(loghandler)
            return

        if not os.path.exists(self.logging_configfile):
            raise exceptions.AgentOptionPathNotFoundException(
                "logging:configfile", self.logging_configfile)

        with open(self.logging_configfile, 'rt') as f:
            config = yaml.load(f.read())
            logging.config.dictConfig(config)

    def _get_config_files(self):
        candidates = ["/etc/dcm/agent.conf",
                      os.path.expanduser("~/.dcm/agent.conf")]

        if _g_conf_file_env in os.environ:
            candidates.append(os.environ[_g_conf_file_env])
        if self._cli_args.conffile:
            candidates.append(self._cli_args.conffile)

        locations = []
        for f in candidates:
            f = os.path.abspath(f)
            if os.path.exists(f):
                locations.append(f)
            else:
                # todo log a warning
                pass

        return locations

    def setup(self, conffile=None, clioptions=False, args=sys.argv):
        if conffile is not None:
            self._parse_config_file(conffile)
        else:
            if clioptions is not None:
                self._parse_command_line(args)
            config_files = self._get_config_files()
            # parse command line options to get all the config files
            for conf_file in config_files:
                self._parse_config_file(conf_file)
        self._setup_logging()

    def console_log(self, level, msg, **kwargs):
        # vb_level = self.get_cli_arg("verbose")
        # if level > vb_level:
        #     return
        # print >> sys.stderr, msg % kwargs
        return

    def set_agent_id(self, agent_id):
        # TODO write to a file
        self._agent_id = agent_id

    def get_agent_id(self):
        return self._agent_id

    def set_handshake(self, handshake_doc):
        #if handshake_doc["version"] == dcm.agent.g_version:
        self._agent_id = handshake_doc["agentID"]
        self.cloud_id = handshake_doc["cloudId"]
        self.customer_id = handshake_doc["customerId"]
        self.region_id = handshake_doc["regionId"]
        self.zone_id = handshake_doc["zoneId"]
        self.server_id = handshake_doc["serverId"]
        self.server_name = handshake_doc["serverName"]
        #self.ephemeral_file_system = handshake_doc["ephemeralFileSystem"]
        #self.encrypted_ephemeral_fs_key = \
        #    handshake_doc["encryptedEphemeralFsKey"]
        #else:
        #    raise exceptions.AgentHandshakeException()

    def get_script_dir(self):
        _ROOT = dcm.agent.get_root_location()
        return os.path.join(_ROOT, 'scripts')

    def get_script_location(self, name):
        script_dir = self.get_script_dir()
        _g_logger.debug("Script Dir %s" % script_dir)
        for platform in self.platform_script_locations:
            _g_logger.debug("Script platform %s" % platform)
            path = os.path.join(script_dir, platform, name)
            _g_logger.debug("Script location %s" % path)
            if os.path.exists(path):
                return path
        return None

    def is_upgrading(self):
        return False

    def is_imaging(self):
        return False

    def lock(self):
        pass

    def unlock(self):
        pass

    def get_service_directory(self, service_name):
        return os.path.join(self.storage_services_dir, service_name)

    def start_job_runner(self):
        self.jr = job_runner.JobRunner()

    def get_temp_file(self, filename):
        new_dir = tempfile.mkdtemp(dir=self.storage_temppath)
        return os.path.join(new_dir, filename)

