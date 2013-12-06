import ConfigParser
import logging
import os
import subprocess
from dcm.agent import exceptions


# The abstract object for plugins.
class Plugin(object):

    def __init__(self, agent, conf, job_id, items_map, name, arguments):
        logname = __name__ + "." + name
        log = logging.getLogger(logname)
        self.agent = agent
        self.logger = logging.LoggerAdapter(log, {'job_id': job_id})
        self.job_id = job_id
        self.name = name
        self.conf = conf
        self.items_map = items_map
        self.arguments = arguments

    @exceptions.AgentNotImplementedException
    def run(self):
        pass

    def __str__(self):
        return self.name + ":" + self.job_id

    def get_name(self):
        return self.name


# a fork plugin.  Fork an executable and wait for it to complete.
class ExePlugin(Plugin):

    def __init__(self, agent, conf, job_id, items_map, name, arguments):
        super(ExePlugin, self).__init__(
            agent, conf, job_id, items_map, name, arguments)
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
        return (stdout, stderr, process.returncode)

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def _load_python(agent, conf, job_id, items_map, name, arguments):
    if 'module_name' not in items_map:
        raise exceptions.AgentPluginConfigException(
            "The configuration for the %s plugin does not contain a "
            "module_name entry." % name)
    module_name = items_map['module_name']
    try:
        module = __import__(module_name)
        return module.load_plugin(
            agent, conf, job_id, items_map, name, arguments)
    except ImportError as iee:
        raise exceptions.AgentPluginConfigException(
            "The module named %s could not be imported." % module_name, iee)
    except AttributeError as ae:
        raise exceptions.AgentPluginConfigException(
            "The module named %s does not have the load function."
            % module_name, ae)


def _load_exe(agent, conf, job_id, items_map, name, arguments):
    return ExePlugin(agent, conf, job_id, items_map, name, arguments)


g_type_to_obj_map = {
    "exe": _load_exe,
    "python_module": _load_python
}


def load_plugin(agent, conf, job_id, name, arguments):
    conffile = conf.plugin_configfile
    if not os.path.exists(conffile):
        raise exceptions.AgentPluginConfigException(
            "The plugin configuration file %s could not be found" % conffile)

    parser = ConfigParser.SafeConfigParser()
    parser.read([conffile])
    section = parser.sections()

    section_name = 'plugin:' + name
    for s in section:
        if s == section_name:
            try:
                items = parser.items(section_name)
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

                func = g_type_to_obj_map[type]
                return func(agent, conf, job_id, items_map, name, arguments)
            except ConfigParser.NoOptionError as conf_ex:
                raise exceptions.AgentPluginConfigException(conf_ex.message)
    raise exceptions.AgentPluginConfigException(
        "Plugin %s was not found." % name)
