#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import os

import dcm.agent.logger as dcm_logger
import dcm.agent.plugins.api.exceptions as plugin_exceptions
import dcm.agent.plugins.api.utils as plugin_api
import dcm.agent.utils as agent_util


_g_logger = logging.getLogger(__name__)


class PluginReply(object):
    """An instance of this class must be returned from the run() method of
    all extension plugins.  It is serialized into a JSON object and sent
    back to DCM as a reply to the associated command.
    """

    def __init__(self, return_code, reply_type="void", reply_object=None,
                 message="", error_message=""):
        """
        :param return_code: 0 for success, non-0 for failure

        :param reply_type: A string which defines the reply_object layout.  For
                           example "void"
        :param reply_object: A module defined reply payload.  The reply_type
                             argument is used to determine this values layout.
        :param message: A string describing a successful action
        :param error_message: A string describing any error that occurred while
                              processing this action.
        """
        self._reply_doc = {
            'return_code': return_code,
            'reply_type': reply_type,
            'reply_object': reply_object,
            'message': message,
            'error_message': error_message
        }

    def get_reply_doc(self):
        return self._reply_doc

    def get_message(self):
        return self._reply_doc['message']

    def set_message(self, msg):
        self._reply_doc['message'] = msg

    def get_return_code(self):
        return self._reply_doc['return_code']


class _ArgHolder(object):
    pass


class Plugin(object):
    """This is the base class that should be used for all plugins.  It handles
    the processing needed to validate and parse the protocol.  When defining
    a new plugin two class level variables should be defined.

    :var protocol_arguments: This is a dictionary of arguments that the
                             command will expect/accept from DCM.  It has the
                             following format.

                             .. code-block:: python

                                { <argument name> :
                                   (<human readable description string,
                                    <True | False bool that states if the argument is mandatory>,
                                    <argument type conversion function.  This converts a byte string
                                     into the needed python type.  Some base functions can be found
                                     in utils>,
                                     <Default value>),
                                }

    :var command_name: The name of this command.  This must be globally
                       unique for all the commands in a given agent.  It can
                       be defined by the module in order to tell the
                       dcm-agent-add-plugin program the desired name, however
                       ultimately it will be set by the agent and the
                       value may be different than the desired name.

    :var long_runner: The variable long_runner can be set on the class
                      to instruct the dcm-agent-add-plugin that this plugin
                      will be run for a long time and should be set up for
                      polling with get_job_description.
    """

    protocol_arguments = {}
    command_name = None

    def __init__(self, conf, request_id, items_map, name, arguments):
        """If the plugin overrides the constructor it must call super on
        the parent constructor and pass in the same values it was passed.

        :param conf: The DCM agent configuration object.  This can be used
                     as a way to discover information about the agent
                     deployment.  As an example conf.platform_name will tell
                     the plugin the linux distribution name (eg: ubuntu).
        :param request_id: This is the request ID for this specific request
                           of the command.  This will be different every time.
                           The plugin will rarely need this information.
        :param items_map: This is an opaque structure that is threaded through
                          the module.  Plugins should only use this when
                          calling super()
        :param name: The name of this command.  This will match
                     cls.command_name
        :param arguments: The arguments that DCM passed into this command.
                          after the parent constructor is called these
                          arguments will be attributes of the self.args object.
        """
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
        except plugin_exceptions.AgentPluginParameterBadValueException:
            raise
        except Exception as ex:
            raise plugin_exceptions.AgentPluginParameterBadValueException(
                self.name, "general", str(ex))

    def _validate_arguments(self):
        # validate that all of the required arguments were sent
        for arg in self.protocol_arguments:
            h, mandatory, t, default = self.protocol_arguments[arg]
            if mandatory and arg not in self.arguments:
                raise plugin_exceptions.AgentPluginParameterNotSentException(
                    self.name, arg)
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
                        raise plugin_exceptions.AgentPluginParameterBadValueException(
                            self.name,
                            "Parameter %s has an invalid value %s" % (arg, a))
                setattr(self.args, arg, a)

    def __str__(self):
        return self.name + ":" + self.job_id

    def get_name(self):
        """This is called by DCM to get the name of the plugin.  This should
        not be overridden.
        :return A string representing the command name:
        """
        return self.name

    def cancel(self, *args, **kwargs):
        """This method is called by the agent when an outstanding command needs
        to be canceled.  The plug in should treat it like a signal to cancel.
        Then it is received the plugin should start canceling its work, however
        it should return from cancel immediately.  Cancel should not block
        until the work is complete.
        """
        pass

    @agent_util.not_implemented_decorator
    def run(self):
        """This method is called by the agent to give the plugin a thread that
        it can use to do its work.  When the plugin is finished it should
        return a PluginReply.

        If the plugin experiences an error while processing it can throw an
        exception from the dcm.agent.plugins.api.exceptions module.
        """
        pass


class ScriptPlugin(Plugin):
    """This base plugin class can be used for plugins that call out to
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
                raise plugin_exceptions.AgentPluginConfigException(
                    "The plugin %s points an add_user_exe_path that does not "
                    "exist." % name)
        except KeyError as ke:
            raise plugin_exceptions.AgentPluginConfigException(
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
        return PluginReply(rc, message=stdout, error_message=stderr)
