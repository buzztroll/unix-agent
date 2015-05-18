import threading

import dcm.agent.utils as utils
import dcm.agent.state_machine as state_machine


class States:
    NEW = "NEW"
    WAITING_FOR_ACK = "WAITING_FOR_ACK"
    COMPLETE = "COMPLETE"


class Events:
    TIMEOUT = "TIMEOUT"
    SEND = "TIMEOUT"
    ACK_RECEIVED = "ACK_RECEIVED"
    STOP = "STOP"


class AlertAckMsg(object):

    def __init__(self, timeout, doc, conn):
        self._timeout = timeout
        self._doc = doc
        self._sm = state_machine.StateMachine(States.NEW)
        self._timer = None
        self._lock = threading.RLock()
        self._conn = conn

    @utils.class_method_sync
    def incoming_message(self):
        self._sm.event_occurred(Events.ACK_RECEIVED, message={})

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    @utils.class_method_sync
    def timeout(self):
        self._sm.event_occurred(Events.TIMEOUT, message={})

    @utils.class_method_sync
    def send(self):
        self._sm.event_occurred(Events.SEND, message={})

    def _send_timeout(self):
        self._timer = threading.Timer(self._timeout, self.timeout)
        self._conn.send(self._doc)

    def _sm_send_message(self):
        self._send_timeout()

    def _sm_ack_received(self):
        # the timer must be active
        self._timer.cancel()
        self._timer = None

    def _sm_resend_message(self):
        self._send_timeout()

    def _sm_stopping_early(self):
        self._timer.cancel()
        self._timer = None

    def setup_states(self):
        self._sm.add_transition(States.NEW,
                                Events.SEND,
                                States.WAITING_FOR_ACK,
                                self._sm_send_message)
        self._sm.add_transition(States.NEW,
                                Events.STOP,
                                States.NEW,
                                None)

        self._sm.add_transition(States.WAITING_FOR_ACK,
                                Events.TIMEOUT,
                                States.WAITING_FOR_ACK,
                                self._sm_resend_message)
        self._sm.add_transition(States.WAITING_FOR_ACK,
                                Events.ACK_RECEIVED,
                                States.COMPLETE,
                                self._sm_ack_received)
        self._sm.add_transition(States.WAITING_FOR_ACK,
                                Events.STOP,
                                States.COMPLETE,
                                self._sm_stopping_early)

        self._sm.add_transition(States.COMPLETE,
                                Events.ACK_RECEIVED,
                                States.COMPLETE,
                                None)
        self._sm.add_transition(States.COMPLETE,
                                Events.TIMEOUT,
                                States.COMPLETE,
                                None)
        self._sm.add_transition(States.COMPLETE,
                                Events.STOP,
                                States.COMPLETE,
                                None)
