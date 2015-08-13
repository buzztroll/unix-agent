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
"""This module contains a set of exceptions that can be thrown from dcm-agent
extension plugins.
"""
import dcm.agent.exceptions as agent_exceptions


class AgentPluginException(agent_exceptions.AgentBaseException):
    """
    The base class for all agent plugin exceptions
    """
    pass


class AgentPluginConfigException(AgentPluginException):
    """
    The base class for plugin configuration errors.  This is thrown when
    there is an error in the he plugin.conf file.
    """
    pass


class AgentPluginParameterNotSentException(AgentPluginException):
    """
    This is thrown when a mandatory exception is expected but not received.
    """
    def __init__(self, command_name, argument_name):
        message = ("The command %(command_name)s requires the arguments "
                   "%(argument_name)s and it was not found."
                   % locals())
        super(AgentPluginParameterNotSentException, self).__init__(message)


class AgentPluginParameterBadValueException(AgentPluginException):
    """
    This is thrown when a parameter has an invalid value.
    """
    def __init__(self, command_name, argument_name, expected_values=None):
        message = ("The command %(command_name)s received a bad value for "
                   "the argument name %(argument_name)s.")
        if expected_values is not None:
            message = message + "  %(expected_values)s"
        message = message % locals()
        super(AgentPluginParameterBadValueException, self).__init__(message)


class AgentPluginOperationException(AgentPluginException):
    """
    This is thrown when something goes wrong while processing the command.
    """
    pass
