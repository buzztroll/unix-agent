import logging
import os
import sys

import dcm.agent.exceptions as exceptions


_g_logger = logging.getLogger(__name__)


class StateMachine(object):

    def __init__(self, start_state):
        self._state_map = {}
        self._current_state = start_state
        self._user_callbacks_list = []
        self._event_list = []

    def add_transition(self, state_event, event, new_state, func):
        if state_event not in self._state_map:
            self._state_map[state_event] = {}
        self._state_map[state_event][event] = (new_state, func)

    def mapping_to_digraph(self, outf=None):
        if outf is None:
            outf = sys.stdout
        outf.write('digraph {' + os.linesep)
        outf.write('node [shape=circle, style=filled, fillcolor=gray, '
                   'fixedsize=true, fontsize=11, width=1.5];')
        for start_state in self._state_map:
            for event in self._state_map[start_state]:
                ent = self._state_map[start_state][event]
                if ent is not None:
                    outf.write('%s  -> %s [label=" %s ", fontsize=11];'
                               % (start_state, ent[0], event) + os.linesep)
        outf.write('}' + os.linesep)
        outf.flush()

    def event_occurred(self, event, **kwargs):
        try:
            old_state = self._current_state
            new_state, func = self._state_map[self._current_state][event]
            # a logging adapter is added so that me can configure more of the
            # log line in a conf file
            log_msg = ("Event %(event)s occurred.  Moving from state "
                       "%(old_state)s to %(new_state)s") % locals()
            _g_logger.debug(log_msg)
            self._event_list.append((event, old_state, new_state))
            if func is not None:
                try:
                    _g_logger.debug("Calling %s | %s" % (func.__name__,
                                                         func.__doc__))
                    func(**kwargs)
                    self._current_state = new_state
                    _g_logger.debug("Moved to new state %s." % new_state)
                except exceptions.DoNotChangeStateException as dncse:
                    _g_logger.warning("An error occurred that permits us "
                                      "to continue but skip the state "
                                      "change. %s" % str(dncse))
                except Exception as ex:
                    _g_logger.exception("An exception occurred %s")
                    raise
        except KeyError as keyEx:
            raise exceptions.IllegalStateTransitionException(
                event, self._current_state)

    def get_event_list(self):
        return self._event_list
