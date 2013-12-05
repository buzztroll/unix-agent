import logging

import dcm.agent.exceptions as exceptions
import dcm.agent.messaging.utils as utils


class RequesterEvents(object):
    REQUEST_MADE = "REQUEST_MADE"
    TIMEOUT = "TIMEOUT"
    ACK_RECEIVED = "ACK"
    REPLY_RECEIVED = "REPLY"
    NACK_RECEIVED = "NACK"
    CANCEL_REQUESTED = "CANCEL"
    CALLBACK_RETURNED = "CALLBACK"
    CLEANUP_TIMEOUT = "CLEANUP_TIMEOUT"


class RequesterStates(object):
    REQUEST_NEW = "NEW"
    REQUESTING = "REQUESTING"
    REQUESTED = "REQUESTED"
    REQUEST_FAILING = "REQUEST_FAILING"
    USER_CALLBACK = "USER_CALLBACK"
    SENDING_ACK = "SENDING_ACK"
    ACK_SENT = "ACK_SENT"
    CLEANUP = "CLEANUP"


class ReplyEvents(object):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REPLY_ACK_RECEIVED = "REPLY_ACK"
    REPLY_NACK_RECEIVED = "REPLY_NACK"
    CANCEL_RECEIVED = "CANCEL"
    USER_ACCEPTS_REQUEST = "ACCEPTED"
    USER_REJECTS_REQUEST = "REJECTED"
    USER_REPLIES = "USER_REPLIES"
    TIMEOUT = "TIMEOUT"


class ReplyStates(object):
    NEW = "NEW"
    REQUESTING = "REQUESTING"
    CANCEL_RECEIVED_REQUESTING = "CANCEL_RECEIVED_REQUESTING"
    ACKED = "ACKED"
    REPLY = "REPLY"
    NACKED = "NACKED"
    CLEANUP = "CLEANUP"


class UserCallback(object):

    def __init__(self, func, args, kwargs):
        self._func = func
        self._args = args
        if args is None:
            self._args = []
        self._kwargs = kwargs
        if kwargs is None:
            self._kwargs = {}
        self._log = utils.MessageLogAdaptor(logging.getLogger(__name__), {})


    def call(self):
        try:
            self._log.debug("UserCallback calling %s" % self._func.__name__)
            self._func(*self._args, **self._kwargs)
        except Exception as ex:
            self._log.error("UserCallback function %(func_name)s threw "
                            "exception %(ex)s" %
                            {'func_name': self._func.__name__,
                             'ex': str(ex)})
            raise
        finally:
            self._log.debug("UserCallback function %s returned successfully."\
                % self._func.__name__)


class StateMachine(object):

    def __init__(self, start_state):
        self._state_map = {}
        self._current_state = start_state
        self._user_callbacks_list = []
        self._log = utils.MessageLogAdaptor(logging.getLogger(__name__), {})

    def add_transition(self, state_event, event, new_state, func):
        if state_event not in self._state_map:
            self._state_map[state_event] = {}
        self._state_map[state_event][event] = (new_state, [func])

    def add_transition_callback(self, state, event, func, pos=0):
        if state not in self._state_map:
            raise Exception()
        if event not in self._state_map[state]:
            raise Exception()

        state, event_list = self._state_map[state][event]
        event_list.insert(pos, func)

    def mapping_to_digraph(self):
        print 'state_machine {'
        for start_state in self._state_map:
            for event in self._state_map[start_state]:
                ent = self._state_map[start_state][event]
                if ent is not None:
                    print '%s  -> %s [ label = "%s" ];' % (start_state, ent[0],
                                                           event)
        print '}'

    def event_occurred(self, event, **kwargs):
        try:
            new_state, func_list = self._state_map[self._current_state][event]
            # a logging adapter is added so that me can configure more of the
            # log line in a conf file
            log_msg = ("Event %(event)s occurred.  Moving from state " \
                       "%(current_state)s to %(new_state)s") % \
                           {'event': event,
                            'current_state': self._current_state,
                            'new_state': new_state}
            self._log.info(log_msg)
            for func in func_list:
                if func is not None:
                    try:
                        self._log.info("Calling %s" % func.__name__)
                        self._log.debug("Calling %s | %s" % (func.__name__,
                                                             func.__doc__))
                        func(**kwargs)
                        self._current_state = new_state
                        self._log.info("Moved to new state %s." % new_state)
                    except exceptions.DoNotChangeStateException as dncse:
                        self._log.warning("An error occurred that permits us "
                                          "to continue but skip the state "
                                          "change. %s" % str(dncse))
                    except Exception as ex:
                        self._log.error("An exception occurred %s" % str(ex))
                        raise
        except KeyError as keyEx:
            raise exceptions.IllegalStateTransitionException(
                event, self._current_state)

    def register_user_callback(self, func, args=None, kwargs=None):
        cb = UserCallback(func, args, kwargs)
        self._user_callbacks_list.append(cb)

    def process_callbacks(self):
        for cb in self._user_callbacks_list:
            cb.call()
