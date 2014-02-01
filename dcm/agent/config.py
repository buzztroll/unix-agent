import argparse
import ConfigParser
import logging
import logging.config
import os
import yaml
import dcm
from dcm.agent.connection import websocket

import dcm.agent.exceptions as exceptions
import dcm.agent.connection.dummy as dummy_con
import dcm.agent.tests.utils.test_connection as test_connection


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
                 options=None, minv=None, maxv=None):
        self.section = section
        self.name = name
        self.my_type = t
        self.options = options
        self.default = default
        self.minv = minv
        self.maxv = maxv

    def get_value(self, parser):
        try:
            v = parser.get(self.section, self.name, self.default)
        except ConfigParser.NoOptionError:
            v = self.default
        except ConfigParser.NoSectionError:
            v = self.default
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

    def __init__(self, section, name, relative_path=None, default=None):
        super(FilenameOpt, self).__init__(section, name, str, default=default)
        self.relative_path = relative_path

    def get_value(self, parser):
        v = super(FilenameOpt, self).get_value(parser)
        if v is None:
            return None
        if not os.path.isabs(v):
            v = os.path.join(self.relative_path, v)
        return os.path.abspath(v)


class AgentConfig(object):
    top_logger = 'dcm.agent'

    def __init__(self):
        self._cli_args = None
        self._remaining_argv = None
        self._agent_id = None
        self.services_path = None # TODO SET THIS
        self.ephemeral_mount_point = None # TODO SET THIS
        self.services_directory = None # TODO SET THIS
        self.enstratius_directory = None # TODO SET THIS

    def _parse_command_line(self):
        conf_parser = argparse.ArgumentParser(
            description="Start the agent")
        conf_parser.add_argument(
            "-c", "--conffile", help="Specify config file", metavar="FILE",
            default=None)
        conf_parser.add_argument("-v", "--verbose", action="count",
                                 help="Display more output on the console.",
                                 default=0)
        self._cli_args, self._remaining_argv = conf_parser.parse_known_args()

    def get_cli_arg(self, key):
        return getattr(self._cli_args, key, None)

    def _parse_config_file(self, config_file):

        relative_path = os.path.dirname(config_file)

        option_list = [
            ConfigOpt("pydev", "host", str, default=None, options=None),
            ConfigOpt("pydev", "port", int, default=None, options=None),

            ConfigOpt("workers", "count", int, default=4, options=None),

            ConfigOpt("connection", "type", str, default=None, options=None),
            ConfigOpt("connection", "hostname", str, default=None),
            FilenameOpt("connection", "source_file",
                        relative_path=relative_path, default=None),
            FilenameOpt("connection", "dest_file",
                        relative_path=relative_path, default=None),
            ConfigOpt("connection", "port", int, default=5309, options=None),

            FilenameOpt("logging", "configfile", relative_path=relative_path,
                        default=None),

            FilenameOpt("plugin", "configfile", relative_path=relative_path),

            FilenameOpt("storage", "temppath", relative_path=relative_path),
            FilenameOpt("storage", "idfile", relative_path=relative_path),
            FilenameOpt("storage", "script_dir", relative_path=relative_path),

            ConfigOpt("cloud", "name", str, default=None),
            ConfigOpt("cloud", "metadata_url", str,
                      default="http://169.254.169.254/1.0/meta-data"),

            ConfigOpt("messaging", "retransmission_timeout", float,
                      default=5),
            ConfigOpt("messaging", "max_at_once", int, default=-1),

            ConfigOpt("enstratius", "agentmanager_url", str, default=None),
            ConfigOpt("platform", "script_locations", list, default="SmartOS"),
        ]
        parser = ConfigParser.SafeConfigParser()
        parser.read(config_file)

        for opt in option_list:
            try:
                v = opt.get_value(parser)
                config_variable = opt.section + '_' + opt.name
                self.__setattr__(config_variable, v)
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

    def setup(self, conffile=None, clioptions=False):
        if conffile is not None:
            self._parse_config_file(conffile)
        else:
            if clioptions is not None:
                self._parse_command_line()
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
        if handshake_doc["version"] == "1":
            self._agent_id = handshake_doc["version"]
            self.cloud_id = handshake_doc["cloudId"]
            self.customer_id = handshake_doc["customerId"]
            self.region_id = handshake_doc["regionId"]
            self.zone_id = handshake_doc["zoneId"]
            self.server_id = handshake_doc["serverId"]
            self.server_name = handshake_doc["serverName"]
            self.ephemeral_file_system = handshake_doc["ephemeralFileSystem"]
            self.encrypted_ephemeral_fs_key = \
                handshake_doc["encryptedEphemeralFsKey"]
        else:
            raise exceptions.AgentHandshakeException()

    def get_script_dir(self):
        _ROOT = dcm.agent.get_root_location()
        return os.path.join(_ROOT, 'scripts')

    def get_script_location(self, name):
        script_dir = self.get_script_dir()
        for platform in self.platform_script_locations:
            path = os.path.join(script_dir, platform, name)
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
        return os.path.join(self.services_directory, service_name)
