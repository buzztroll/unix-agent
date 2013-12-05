
class AgentNotImplementedException(Exception):
    def __init__(self, func_name):
        message = "The function %s must be implemented." % (func_name)
        super(AgentNotImplementedException, self).__init__(message)

class AgentOptionException(Exception):
    pass


class AgentOptionTypeException(AgentOptionException):
    def __init__(self, name, expected_type, given_value):
        message = ("The config option %(name)s had the value "
                   "%(given_value)s could not be converted "
                   "to %(expected_type)s" % locals())
        super(AgentOptionTypeException, self).__init__(message)


class AgentOptionSectionNotFoundException(AgentOptionException):
    def __init__(self, name):
        message = ("The section %(name)s is required and was not "
                   "found" % locals())
        super(AgentOptionSectionNotFoundException, self).__init__(message)


class AgentOptionValueException(AgentOptionException):
    def __init__(self, name, given_value, expected_values):
        message = ("The config option %(name)s must have one of the "
                   "values %(expected_values)s not %(given_value)" % locals())
        super(AgentOptionValueException, self).__init__(message)


class AgentOptionValueNotSetException(AgentOptionException):
    def __init__(self, name):
        message = ("The config option %(name)s must be set." % locals())
        super(AgentOptionValueException, self).__init__(message)


class AgentOptionPathNotFoundException(AgentOptionException):
    def __init__(self, name, path):
        message = ("The config option %(name)s points to an invalid path: "
                   "%(path)s " % locals())
        super(AgentOptionPathNotFoundException, self).__init__(message)


class AgentOptionRangeException(AgentOptionException):
    def __init__(self, name, given_value, minv, maxv):
        message = ("The config option %(name)s must be between %(minv) "
                   "and %(maxv)s not %(given_value)" % locals())
        super(AgentOptionValueException, self).__init__(message)


class AgentPluginConfigException(Exception):
    pass


class AgentPluginMessageException(Exception):
    pass


class StateMachineException(Exception):
    pass


class DoNotChangeStateException(StateMachineException):
    pass


class IllegalStateTransitionException(StateMachineException):
    msg = "The event %(event)s is not valid when in state %(state)s"

    def __init__(self, event, state):
        super(IllegalStateTransitionException, self).__init__(
            self.msg % {"event": event, "state": state})


class AssertionFailure(Exception):
    pass


class MessagingException(Exception):
    pass


class RequesterMessagingException(MessagingException):
    pass


class MalformedMessageException(MessagingException):
    pass


class MissingMessageParameterException(MalformedMessageException):
    msg = "The message requires the attribute %(missing_name)s but " \
          "it was not found."

    def __init__(self, missing_name):
        super(MissingMessageParameterException, self).__init__(
            self.msg % {'missing_name': missing_name})


class InvalidMessageParameterValueException(MalformedMessageException):
    msg = "The attribute %(attr_name)s is set to the illegal value " \
          "%(attr_value)s."

    def __init__(self, attr_name, attr_value):
        super(InvalidMessageParameterValueException, self).__init__(
            self.msg % {'attr_name': attr_name,
                        'attr_value': attr_value})


class PerminateConnectionException(MessagingException):
    msg = "This connection has perminately failed.  This should almost " \
          "never happen. %(details)s."

    def __init__(self, details):
        super(PerminateConnectionException, self).__init__(self.msg % locals())

