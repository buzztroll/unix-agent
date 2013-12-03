
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