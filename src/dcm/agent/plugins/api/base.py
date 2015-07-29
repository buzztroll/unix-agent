import logging
import os

import dcm.agent.logger as dcm_logger
import dcm.agent.plugins.api.utils as plugin_api
import dcm.agent.exceptions as exceptions
import dcm.agent.utils as agent_util


_g_logger = logging.getLogger(__name__)


class PluginInterface(object):

    @agent_util.not_implemented_decorator
    def call(self, name, logger, arguments, **kwargs):
        pass

    @agent_util.not_implemented_decorator
    def cancel(self, reply_rpc, *args, **kwargs):
        pass

    @agent_util.not_implemented_decorator
    def get_name(self):
        pass


class _ArgHolder(object):
    pass


class Plugin(PluginInterface):

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
        self.args = _ArgHolder()
        try:
            self._validate_arguments()
        except exceptions.AgentPluginBadParameterException:
            raise
        except Exception as ex:
            raise exceptions.AgentPluginBadParameterException(
                self.name, str(ex))

    def _validate_arguments(self):
        # validate that all of the required arguments were sent
        for arg in self.protocol_arguments:
            h, mandatory, t, default = self.protocol_arguments[arg]
            if mandatory and arg not in self.arguments:
                raise exceptions.AgentPluginParameterException(self.name, arg)
            setattr(self.args, arg, default)

        # validate that nothing extra was sent
        for arg in self.arguments:
            if arg not in self.protocol_arguments:
                dcm_logger.log_to_dcm_console_unknown_job_parameter(
                    job_name=self.name,
                    parameter_name=arg)
            else:
                h, mandatory, t, default = self.protocol_arguments[arg]
                a = self.arguments[arg]
                if a is not None:
                    try:
                        a = t(a)
                    except Exception as ex:
                        _g_logger.exception(str(ex))
                        raise exceptions.AgentPluginBadParameterException(
                            self.name, "Parameter %s has an invalid "
                                       "value %s" % (arg, a))
                setattr(self.args, arg, a)

    def __str__(self):
        return self.name + ":" + self.job_id

    def get_name(self):
        return self.name

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


class ScriptPlugin(Plugin):
    """
    This base plugin class can be used for plugins that call out to
    scripts.  The ordered_param_list member variable must be set with the
    parameters that the called script needs.  The script name is
    pulled from the plug ins configuration section, ex:

    [plugin:add_user]
    type: python_module
    module_name: dcm.agent.plugins.builtin.add_user
    script_name: addUser

    That name is used to locate the absolute path to a script under
    <base location>/bin
    """

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ScriptPlugin, self).__init__(
            conf, job_id, items_map, name, arguments)
        self.ordered_param_list = []
        self.cwd = None

        try:
            script_name = items_map["script_name"]
            self.exe_path = conf.get_script_location(script_name)

            if not os.path.exists(self.exe_path):
                raise exceptions.AgentPluginConfigException(
                    "The plugin %s points an add_user_exe_path that does not "
                    "exist." % name)
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, str(ke)))

    def run(self):
        command_list = [self.exe_path]
        command_list.extend(self.ordered_param_list)
        _g_logger.debug("Plugin running the command %s" % str(command_list))

        _g_logger.debug("Running the remote %s" % self.exe_path)
        (stdout, stderr, rc) = plugin_api.run_command(
            self.conf, command_list, cwd=self.cwd)
        _g_logger.debug("Command %s: stdout %s.  stderr: %s" %
                        (str(command_list), stdout, stderr))
        reply = {"return_code": rc, "message": stdout,
                 "error_message": stderr, "reply_type": "void"}
        return reply
