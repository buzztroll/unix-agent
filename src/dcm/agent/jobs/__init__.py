import ConfigParser
import importlib
import logging
import os
import re
import subprocess
from dcm.agent import exceptions, utils


_g_logger = logging.getLogger(__name__)


class ArgHolder(object):
    pass


# The abstract object for plugins.
class Plugin(object):

    # The following class variables will help with self documentation of
    # the protocol.
    #
    # the protocol arguments will be the command arguments that the protocol
    # supports.  It is a mapping from name to the tuple:
    # (help message, required)
    protocol_arguments = {}
    # the command name is the wire protocol name of the command
    command_name = None

    def __init__(self, conf, request_id, items_map, name, arguments):
        logname = __name__ + "." + name
        log = logging.getLogger(logname)
        self.logger = logging.LoggerAdapter(log, {'job_id': request_id})
        self.job_id = request_id
        self.name = name
        self.conf = conf
        self.items_map = items_map
        self.arguments = arguments
        self.args = ArgHolder()
        self._validate_arguments()

    def _validate_arguments(self):
        # validate that all of the required arguments were sent
        for arg in self.protocol_arguments:
            h, mandatory, t = self.protocol_arguments[arg]
            if mandatory and arg not in self.arguments:
                raise exceptions.AgentPluginParameterException(self.name, arg)
            setattr(self.args, arg, None)

        # validate that nothing extra was sent
        for arg in self.arguments:
            if arg not in self.protocol_arguments:
                _g_logger.warn("The argument %s was sent from the agent "
                               "manager but is not understood by this "
                               "command.")
            else:
                h, mandatory, t = self.protocol_arguments[arg]
                a = self.arguments[arg]
                if a is not None:
                    a = t(a)
                setattr(self.args, arg, a)

    @utils.not_implemented_decorator
    def run(self):
        pass

    def __str__(self):
        return self.name + ":" + self.job_id

    def get_name(self):
        return self.name


# a fork plugin.  Fork an executable and wait for it to complete.
class ExePlugin(Plugin):

    def __init__(self, conf, request_id, items_map, name, arguments):
        super(ExePlugin, self).__init__(
            conf, request_id, items_map, name, arguments)
        if 'path' not in items_map:
            raise exceptions.AgentPluginConfigException(
                "The configuration for the %s plugin does not have "
                "an path entry." % name)
        exe_path = items_map['path']
        if not os.path.exists(exe_path):
            raise exceptions.AgentPluginConfigException(
                "Module %s is misconfigured.  The path %s "
                "does not exists" % (name, exe_path))
        self.exe = os.path.abspath(exe_path)
        self.cwd = os.path.dirname(self.exe)

    def run(self):
        try:
            return self._exec()
        except Exception as ex:
            self.logger.error("Error running the subprocess", ex)

    def _exec(self):
        args = [self.exe]
        args.extend(self.arguments)
        self.logger.info("Forking the command " + str(args))
        args = ' '.join(args)  # for some reason i cannot just pass the array.
                               # at least should do a shell join
        process = subprocess.Popen(args,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   cwd=self.cwd)

        # TODO interate over the output so that it does not all come just at
        # the end
        stdout, stderr = process.communicate()

        self.logger.info("STDOUT: " + str(stdout))
        self.logger.info("STDERR: " + str(stderr))
        self.logger.info("Return code: " + str(process.returncode))
        return {"stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


# we should use stevedore for this
def load_python_module(
        module_name, conf, request_id, items_map, name, arguments):
    try:
        module = importlib.import_module(module_name)
        _g_logger.debug("Module acquired " + str(dir(module)))
        rc = module.load_plugin(conf, request_id, items_map, name, arguments)
        return rc
    except ImportError as iee:
        raise exceptions.AgentPluginConfigException(
            "The module named %s could not be imported." % module_name, iee)
    except AttributeError as ae:
        _g_logger.exception("Could not load " + module_name)
        raise exceptions.AgentPluginConfigException(
            "The module named %s does not have the load function."
            % module_name, ae)
    except:
        _g_logger.exception("An exception occurred loading the module")
        raise


def _load_exe(conf, request_id, items_map, name, arguments):
    return ExePlugin(conf, request_id, items_map, name, arguments)


def _load_python(conf, request_id, items_map, name, arguments):
    if 'module_name' not in items_map:
        raise exceptions.AgentPluginConfigException(
            "The configuration for the %s plugin does not contain a "
            "module_name entry." % name)
    module_name = items_map['module_name']
    return load_python_module(
        module_name, conf, request_id, items_map, name, arguments)


g_type_to_obj_map = {
    "exe": _load_exe,
    "python_module": _load_python
}


def load_plugin(conf, items_map, request_id, name, arguments):
    _g_logger.debug("ENTER load_plugin")
    type = items_map["type"]
    if type not in g_type_to_obj_map:
        raise exceptions.AgentPluginConfigException(
            "The module type %s is not valid." % type)

    func = g_type_to_obj_map[type]
    _g_logger.debug("calling load function")
    return func(conf, request_id, items_map, name, arguments)


def parse_plugin_doc(conf, name):
    _g_logger.debug("ENTER load_plugin")

    conffile = conf.plugin_configfile
    if conffile is None or not os.path.exists(conffile):
        raise exceptions.AgentPluginConfigException(
            "The plugin configuration file %s could not be found" % conffile)

    parser = ConfigParser.SafeConfigParser()
    parser.read([conffile])
    section = parser.sections()

    section_name = 'plugin:' + name
    for s in section:
        p = re.compile(s + "$")
        if p.match(section_name):
            _g_logger.debug(
                "load_plugin: found a match %s: %s" % (s, section_name))

            try:
                items = parser.items(s)
                items_map = {}
                for i in items:
                    items_map[i[0]] = i[1]

                if "type" not in items_map:
                    raise exceptions.AgentPluginConfigException(
                        "The section %s does not have an entry for type."
                        % section_name)
                type = items_map["type"]
                if type not in g_type_to_obj_map:
                    raise exceptions.AgentPluginConfigException(
                        "The module type %s is not valid." % type)

                return items_map
            except ConfigParser.NoOptionError as conf_ex:
                raise exceptions.AgentPluginConfigException(conf_ex.message)

    raise exceptions.AgentPluginConfigException(
        "Plugin %s was not found." % name)
