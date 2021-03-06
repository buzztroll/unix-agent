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
import sys

import dcm.agent.exceptions as exceptions


_g_logger = logging.getLogger(__name__)


class StateMachine(object):

    def __init__(self, start_state, logger=None):
        self._state_map = {}
        self._current_state = start_state
        self._user_callbacks_list = []
        self._event_list = []
        if logger is None:
            self._logger = _g_logger
        else:
            self._logger = logger

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
            self._logger.debug(log_msg)
            self._event_list.append((event, old_state, new_state))
            try:
                if func is not None:
                    self._logger.debug("Calling %s | %s" % (func.__name__,
                                                            func.__doc__))
                    func(**kwargs)
                self._current_state = new_state
                self._logger.debug("Moved to new state %s." % new_state)
            except exceptions.DoNotChangeStateException as dncse:
                self._logger.warning("An error occurred that permits us "
                                     "to continue but skip the state "
                                     "change. %s" % str(dncse))
            except Exception as ex:
                self._logger.exception("An exception occurred %s")
                raise
        except KeyError as keyEx:
            raise exceptions.IllegalStateTransitionException(
                event, self._current_state)

    def get_event_list(self):
        return self._event_list
