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


class AgentBaseException(Exception):
    pass


class AgentNotImplementedException(AgentBaseException):
    def __init__(self, func_name):
        message = "The function %s must be implemented." % (func_name)
        super(AgentNotImplementedException, self).__init__(message)


class AgentOptionException(AgentBaseException):
    pass


class AgentExtrasNotInstalledException(AgentBaseException):
    def __init__(self, exmsg):
        message = "The package install failed with: %s" % exmsg
        super(AgentExtrasNotInstalledException, self).__init__(message)


class AgentPageNotFoundException(AgentBaseException):
    def __init__(self, page_token):
        message = ("The page set with token %(page_token)s was not found."
                   % locals())
        super(AgentPageNotFoundException, self).__init__(message)


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
                   "values %(expected_values)s not %(given_value)s" % locals())
        super(AgentOptionValueException, self).__init__(message)


class AgentOptionValueNotSetException(AgentOptionException):
    def __init__(self, name, msg=None):
        message = ("The config option %(name)s must be set." % locals())
        if msg:
            message = message + " " + msg
        super(AgentOptionValueNotSetException, self).__init__(message)


class AgentOptionValueAlreadySetException(AgentOptionException):
    def __init__(self, opt_name, msg=None):
        message = ("%(opt_name)s has already been used." % locals())
        if msg:
            message = message + " " + msg
        super(AgentOptionValueAlreadySetException, self).__init__(message)


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


class AgentConnectionException(Exception):
    def __init__(self, error_code, error_msg):
        message = ("The connection to DCM has failed is an unrecoverable way. "
                   "Error code: %(error_code)s Error Message %(error_msg)s"
                   % locals())
        super(AgentConnectionException, self).__init__(error_msg)


class AgentHandshakeUnknownTypeException(AgentBaseException):
    pass


class StateMachineException(AgentBaseException):
    pass


class DoNotChangeStateException(StateMachineException):
    pass


class IllegalStateTransitionException(StateMachineException):
    msg = "The event %(event)s is not valid when in state %(state)s"

    def __init__(self, event, state):
        super(IllegalStateTransitionException, self).__init__(
            self.msg % {"event": event, "state": state})


class AssertionFailure(AgentBaseException):
    pass


class MessagingException(AgentBaseException):
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


class AgentHandshakeException(Exception):
    def __init__(self, handshake_doc, extra_msg=None):
        if handshake_doc:
            msg = "The handshake failed with code %s."\
                  % handshake_doc.reply_type
        else:
            msg = "Handshake Error."
        if extra_msg:
            msg = msg + " " + extra_msg
        super(AgentHandshakeException, self).__init__(msg)


class PerminateConnectionException(MessagingException):
    msg = "This connection has perminately failed.  This should almost " \
          "never happen. %(details)s."

    def __init__(self, details):
        super(PerminateConnectionException, self).__init__(self.msg % locals())


class AgentRuntimeException(AgentBaseException):
    pass


class AgentFilePermissionsException(AgentBaseException):
    pass


class AgentConnectionDriverException(AgentBaseException):
    pass


class AgentExecutableException(AgentBaseException):
    msg = "The external process run with %(command_line)s returned an " \
          "error. rc=%(rc)s stderr=%(stderr)s stdout=%(stdout)s"

    def __init__(self, command_line, rc, stdout, stderr):
        super(AgentExecutableException, self).__init__(self.msg % locals())


class AgentUnsupportedCloudFeature(AgentBaseException):
    pass


class PersistenceException(AgentBaseException):
    pass


class AgentPlatformNotDetectedException(AgentBaseException):
    def __init__(self):
        message = ("The platform was not detected")
        super(AgentPlatformNotDetectedException, self).__init__(message)
