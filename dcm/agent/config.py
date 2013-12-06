import argparse
import ConfigParser
import logging
import logging.config
import os
import yaml

import dcm.agent.exceptions as exceptions
import dcm.agent.tests.utils.test_connection as test_connection


_g_conf_file_env = "DCM_AGENT_CONF"


def get_connection_object(conf):
    con_type = conf.connection_type
    if not con_type:
        raise exceptions.AgentOptionValueNotSetException("connection_type")

    # XXX should we stevedore load this or __import__ it or go with a
    # hard coded list?  for now hard coded list

    if con_type == "success_tester":
        source_file = conf.connection_source_file
        fptr = open(source_file, "r")
        outf = open(conf.connection_dest_file, "w")
        return test_connection.TestReplySuccessfullyAlways(fptr, outf)


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
        if v is None:
            return v
        try:
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
        if not os.path.isabs(v):
            v = os.path.join(self.relative_path, v)
        return os.path.abspath(v)


class AgentConfig(object):
    top_logger = 'dcm.agent'
    job_logger = 'dcm.agent.job'

    def __init__(self):
        pass

    def _parse_command_line(self):
        conf_parser = argparse.ArgumentParser(
            description="Start the agent")
        conf_parser.add_argument(
            "-c", "--conffile", help="Specify config file", metavar="FILE",
            default=None)
        self._cli_args, self._remaining_argv = conf_parser.parse_known_args()

    def _parse_config_file(self, config_file):

        relative_path = os.path.dirname(config_file)

        option_list = [
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
        ]
        parser = ConfigParser.SafeConfigParser()
        parser.read(config_file)

        for opt in option_list:
            try:
                v = opt.get_value(parser)
                config_variable = opt.section + '_' + opt.name
                self.__setattr__(config_variable, v)
            except ConfigParser.NoSectionError as nse:
                raise exceptions.AgentOptionSectionNotFoundException(
                    opt.section)

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

    def setup(self, conffile=None, clioptions=None):
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
