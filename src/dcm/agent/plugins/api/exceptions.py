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
