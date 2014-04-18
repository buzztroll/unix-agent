import logging
import uuid
from dcm.agent import parent_receive_q

import dcm.agent.exceptions as exceptions
import dcm.agent.messaging.states as states
import dcm.agent.messaging.types as types
import dcm.agent.messaging.utils as utils


_g_logger = logging.getLogger(__name__)


class RequestRPC(object):

    def __init__(self, document, connection, target_id,
                 timeout=5, cleanup_timeout=60,
                 reply_callback=None, reply_args=None, reply_kwargs=None):
        self._doc = document
        self._request_id = str(uuid.uuid4())
        self._sm = states.StateMachine(states.RequesterStates.REQUEST_NEW)
        self._timeout = timeout
        self._reply_callback = reply_callback
        self._reply_args = reply_args
        if reply_args is None:
            self._reply_args = []
        self._reply_kwargs = reply_kwargs
        if reply_kwargs is None:
            self._reply_kwargs = {}
        self._reply_doc = None
        self._completion_timer = None
        self._cleanup_timeout = cleanup_timeout
        self._conn = connection
        self._target = target_id
        self._message_timer = None

        self._setup_states()
        self.ack_sender = 0

    def get_reply(self):
        return self._reply_doc

    def got_reply(self):
        self._sm.event_occurred(states.RequesterEvents.CALLBACK_RETURNED,
                                message={})

    def send(self):
        self._sm.event_occurred(states.RequesterEvents.REQUEST_MADE,
                                message={})

    def cancel(self):
        self._sm.event_occurred(states.RequesterEvents.CANCEL_REQUESTED,
                                message={})

    def _user_reply_callback(self, *args, **kwargs):
        self._reply_callback(*self._reply_args, **self._reply_kwargs)
        self.user_reply_callback_returns()

    def incoming_message(self, json_doc):
        type_to_event = {
            types.MessageTypes.ACK: states.RequesterEvents.ACK_RECEIVED,
            types.MessageTypes.NACK: states.RequesterEvents.NACK_RECEIVED,
            types.MessageTypes.REPLY: states.RequesterEvents.REPLY_RECEIVED
        }
        if 'type' not in json_doc:
            raise exceptions.MissingMessageParameterException('type')
        if json_doc['type'] not in type_to_event:
            raise exceptions.InvalidMessageParameterValueException(
                'type', json_doc['type'])

        # this next call drives the state machine
        self._sm.event_occurred(type_to_event[json_doc['type']],
                                message=json_doc)

    def request_timeout(self, request_message_timer):
        self._sm.event_occurred(states.RequesterEvents.TIMEOUT,
                                message_timer=request_message_timer)

    def ack_sent_timeout(self, timer=None):
        if timer is None:
            timer = self._completion_timer
        self._sm.event_occurred(states.RequesterEvents.CLEANUP_TIMEOUT,
                                timer=timer)

    def user_reply_callback_returns(self):
        self._sm.event_occurred(states.RequesterEvents.CALLBACK_RETURNED,
                                message={})

    def user_failed_callback_returns(self):
        self._sm.event_occurred(states.RequesterEvents.CALLBACK_RETURNED,
                                message={})

    def _send_reply_ack(self):
        # the ack reuses the message id that it is acknowledging
        # this is here just to help track exchanges
        self.ack_sender = self.ack_sender + 1
        if self.ack_sender > 1:
            pass
        message_id = self._reply_doc['message_id']
        reply_ack_doc = {'request_id': self._request_id,
                         'message_id': message_id,
                         'what': 'REPLY_ACK',
                         'ack_sender': self.ack_sender,
                         'type': types.MessageTypes.ACK}
        self.send_doc(reply_ack_doc)
        if self._completion_timer is not None:
            self._completion_timer.cancel()
        self._completion_timer = utils.AckCleanupTimer(self._cleanup_timeout,
                                                       self.ack_sent_timeout)
        self._completion_timer.start()

    def cleanup(self):
        self._session_complete()

    def send_doc(self, doc):
        doc['entity'] = "requester"
        self._conn.send(doc)

    def _session_complete(self):
        # this is called when we know the session is over and it
        # gives us a change to clean everything up
        if self._message_timer:
            self._message_timer.cancel()
        if self._completion_timer:
            self._completion_timer.cancel()

    ###################################################################
    # state machine event handlers
    # ever method that starts with _sm_ is called under the same lock.
    ###################################################################

    def _sm_send_request(self, **kwargs):
        """
        Send a request. This event handler occurs when ever a RPC request is
        sent for the first time.
        """
        _g_logger.info("This initial request has been made.")
        send_doc = {'request_id': self._request_id,
                    'type': types.MessageTypes.REQUEST,
                    'payload': self._doc}
        message_timer = utils.MessageTimer(self._timeout,
                                           self.request_timeout,
                                           send_doc)
        self._send_request_message(message_timer)

    def _send_request_message(self, message_timer):
        self._message_timer = message_timer
        message_timer.send(self._conn)

    def _sm_requesting_timeout(self, **kwargs):
        """
        This event occurs when the timeout associated with a RPC message
        request expires.
        """
        message_timer = kwargs['message_timer']
        # The time out did occur before the message could be acked so we must
        # resend it
        _g_logger.info("Resending message id %s" % message_timer.message_id)
        self._send_request_message(message_timer)

    def _sm_requested_timeout(self, **kwargs):
        """
        This event occurs when the timeout associated with a RPC message
        request expires but the request was already acknowledge.  This
        happens due to a race when attempting to acquire the state machine
        lock.  This should be a somewhat rare occurrence.
        """
        pass

    def _sm_requesting_ack(self, **kwargs):
        """
        This is the standard case where a request is acknowledged by the remote
        side and the requesting side receives the ACK before any timeouts of
        other 1 off events occur.  Pending retransmits will be cancelled.
        """
        message = kwargs['message']

        # note: was are canceling the message but due to various
        # races it is still possible for timeout to occur.  The
        # state machine should account for this.
        self._message_timer.cancel()
        self._message_timer = None

    def _sm_requested_ack(self, **kwargs):
        # This happens when an ack comes after we already
        # received an ack.  Retransmission overlapping with a received ack can
        # cause this.
        # Hopefully this doesnt happen too often.
        pass

    def _sm_requesting_reply_received(self, **kwargs):
        """
        This occurs when a reply is received before an ack is received.
        This should only happen when the ack is lost or when the target decides
        to optimize by using the reply as an ACK.
        """
        message = kwargs['message']
        if self._message_timer is None:
            # The state machine should guarantee that this never happens
            # if it does this is a big error
            msg = ("When a reply happens in the REQUESTING state the message "
                   "should always be in the list.  This situation should "
                   "never occur")
            utils.build_assertion_exception(
                _g_logger, "message not in list", msg)

        if self._reply_doc is not None:
            msg = ("There should be exactly 1 reply received.  Thus is the "
                   "reply_doc attribute is not None something we terribly "
                   "wrong.")
            utils.build_assertion_exception(
                _g_logger, "reply not none", msg)

        self._reply_doc = message

        # note: was are canceling the message but due to various
        # races it is still possible for timeout to occur.  The
        # state machine should account for this.
        if self._message_timer is not None:
            self._message_timer.cancel()
            self._message_timer = None
        else:
            pass


        if self._reply_callback is not None:
            args = [message]
            if self._reply_args:
                args.extend(self._reply_args)

            parent_receive_q.UserCallback(self._user_reply_callback, None, None)

    def _sm_requested_reply_received(self, **kwargs):
        """
        This is the standard case.  After a request is made, and it receives an
        acknowledgment, it later receives a reply.  Here the reply will be
        stored and the state machine will move on.
        """
        message = kwargs['message']
        if self._message_timer is not None:
            msg = ("In the REQUESTED state the message ID should not be in the"
                   " list")
            utils.build_assertion_exception(
                _g_logger, "message in list", msg)

        if self._reply_doc is not None:
            msg = ("There should be exactly 1 reply received.  Thus is the "
                   "reply_doc attribute is not None something we terribly "
                   "wrong.")
            utils.build_assertion_exception(
                _g_logger, "reply doc is not None", msg)

        _g_logger.debug("The incoming reply is %s" % str(message))
        self._reply_doc = message

        if self._reply_callback is not None:
            args = [message]
            if self._reply_args:
                args.extend(self._reply_args)
            parent_receive_q.register_user_callback(
                self._user_reply_callback,
                self._reply_args, self._reply_kwargs)

    def _sm_user_cb_returned(self, **kwargs):
        """
        This is the standard case when the user is notified that a reply has
        been received.  Once the users notification function returns safely
        this event will occur and an ack wll be sent.  A cleanup timeout will
        also be set.  Until this timeout expires this process will respond to
        reply retransmissions with ACKs. After it times out the will be NACKs
        """
        self._send_reply_ack()

    def _sm_requesting_nack_received(self, **kwargs):
        """
        This occurs when in the requesting state and a NACK is received.
        This happens when the remote side cannot (or does not want to) deal
        with the message.  The message is considered failed and the user
        is notified.
        """
        # TODO FIX THIS
        self._register_failed_callback()

    def _sm_requested_nack_received(self, **kwargs):
        """
        This happens when request has been successfully received yet the
        target (or the messaging channel) decides to cancel the connection.
        A NACK can be received at any time and it signals that the session
        has irrecoverably failed.
        """
        # TODO FIX THIS
        self._register_failed_callback()

    def _sm_send_cancel(self, **kwargs):
        """
        This occurs when a user has asked to cancel a message.  If the session
        is not close, or will not imminently close, we simply send a cancel
        message (meaning put a cancel message next in the queue).
        """
        message_id = utils.new_message_id()
        cancel_doc = {'request_id': self._request_id,
                      'message_id': message_id,
                      'type': types.MessageTypes.CANCEL}
        self.send_doc(cancel_doc)

    def _sm_cancel_requested_when_closing(self, **kwargs):
        """
        For various reasons dealing with race conditions it is possible
        for a cancel to be requested after the session is ready to close.
        In these cases the cancel request is just ignored.  Thus we
        simply log the occurrence here.
        """
        pass

    def _sm_usercb_reply(self, **kwargs):
        """
        In this case a retransmission of a reply was received.  This can
        happen if the reply ack was lost or delayed.  Here do nothing and
        instead wait for the user callback to return before sending the
        ack
        """
        pass

    ### XXX TODO FIGURE OUT THIS CASE
    def _sm_acksent_reply_received(self, **kwargs):
        """
        In this case a retransmission of a reply was received after an
        ack was sent.  The user has already safely handled the incoming
        reply so we can just ack that message here
        """
        self._send_reply_ack()

    def _sm_ack_cleanup_timeout(self, **kwargs):
        """
        This happens when the cleanup timer expires.  This indicates that
        the session can be considered over.  Enough time has passed such
        that we feel safe to assume that had the ack been lost we would
        have received a retransmission reply by now.  In some rare cases
        a retransmission has been received and a new timer was started
        after canceling the old timer.  However it was too late to cancel
        the old timer.  This case is detectable, and when detected nothing
        will happen in this function.
        """
        incoming_timer = kwargs['timer']
        if incoming_timer != self._completion_timer:
            # this is the case when a previous timer was cancelled after
            # it was already firing.  When this happens we just wait for
            # the next timer
            raise exceptions.DoNotChangeStateException(
                "This timer is no longer relevant")

        self._session_complete()

    def _sm_failing_cb_returns(self, **kwargs):
        """
        This event occurs after we know the user was successfully notified
        that the session ended.  We can cleanup at this point
        """
        self._session_complete()

    def _sm_nak_in_failed(self):
        """
        This occurs when multiple NACKs are received.  It is just ignored
        """
        pass

    def _sm_ack_sent_reply_received(self, **kwargs):
        """
        This happens when a reply was retransmitted even tho a previous
        reply was received.  The likely cause is that the reply ACK was
        lost.  This should be a rare case and can be ignored.
        """
        pass

    def _sm_nak_when_closing(self, **kwargs):
        """
        This is a very rare case.  This can only happen when a reply has been
        received and a reply ack has been sent.  At this point the RPC has
        successfully completed its mission, however the ACK could get lost
        causing the target (or the network overlay) to retransmit and perhaps
        give up and send a NACK.  We handle this case by doing nothing.
        """
        pass

    def _setup_states(self):
        self._sm.add_transition(states.RequesterStates.REQUEST_NEW,
                                states.RequesterEvents.REQUEST_MADE,
                                states.RequesterStates.REQUESTING,
                                self._sm_send_request)

        self._sm.add_transition(states.RequesterStates.REQUESTING,
                                states.RequesterEvents.TIMEOUT,
                                states.RequesterStates.REQUESTING,
                                self._sm_requesting_timeout)
        self._sm.add_transition(states.RequesterStates.REQUESTING,
                                states.RequesterEvents.ACK_RECEIVED,
                                states.RequesterStates.REQUESTED,
                                self._sm_requesting_ack)
        self._sm.add_transition(states.RequesterStates.REQUESTING,
                                states.RequesterEvents.NACK_RECEIVED,
                                states.RequesterStates.REQUEST_FAILING,
                                self._sm_requesting_nack_received)
        self._sm.add_transition(states.RequesterStates.REQUESTING,
                                states.RequesterEvents.REPLY_RECEIVED,
                                states.RequesterStates.USER_CALLBACK,
                                self._sm_requesting_reply_received)
        self._sm.add_transition(states.RequesterStates.REQUESTING,
                                states.RequesterEvents.CANCEL_REQUESTED,
                                states.RequesterStates.REQUESTING,
                                self._sm_send_cancel)

        self._sm.add_transition(states.RequesterStates.REQUESTED,
                                states.RequesterEvents.ACK_RECEIVED,
                                states.RequesterStates.REQUESTED,
                                self._sm_requested_ack)
        self._sm.add_transition(states.RequesterStates.REQUESTED,
                                states.RequesterEvents.CANCEL_REQUESTED,
                                states.RequesterStates.REQUESTED,
                                self._sm_send_cancel)
        self._sm.add_transition(states.RequesterStates.REQUESTED,
                                states.RequesterEvents.NACK_RECEIVED,
                                states.RequesterStates.REQUEST_FAILING,
                                self._sm_requested_nack_received)
        self._sm.add_transition(states.RequesterStates.REQUESTED,
                                states.RequesterEvents.REPLY_RECEIVED,
                                states.RequesterStates.USER_CALLBACK,
                                self._sm_requested_reply_received)
        self._sm.add_transition(states.RequesterStates.REQUESTED,
                                states.RequesterEvents.TIMEOUT,
                                states.RequesterStates.REQUESTED,
                                self._sm_requested_timeout)

        self._sm.add_transition(states.RequesterStates.USER_CALLBACK,
                                states.RequesterEvents.REPLY_RECEIVED,
                                states.RequesterStates.USER_CALLBACK,
                                self._sm_usercb_reply)
        self._sm.add_transition(states.RequesterStates.USER_CALLBACK,
                                states.RequesterEvents.CANCEL_REQUESTED,
                                states.RequesterStates.USER_CALLBACK,
                                self._sm_cancel_requested_when_closing)
        self._sm.add_transition(states.RequesterStates.USER_CALLBACK,
                                states.RequesterEvents.CALLBACK_RETURNED,
                                states.RequesterStates.ACK_SENT,
                                self._sm_user_cb_returned)
        #  the next one is a super rare case where the timeout expires
        # but before it can get the lock the remote ends ack is processed
        # and the users callback returns.  XXX TODO make its own CB
        self._sm.add_transition(states.RequesterStates.USER_CALLBACK,
                                states.RequesterEvents.TIMEOUT,
                                states.RequesterStates.USER_CALLBACK,
                                self._sm_requested_timeout)

        self._sm.add_transition(states.RequesterStates.REQUEST_FAILING,
                                states.RequesterEvents.NACK_RECEIVED,
                                states.RequesterStates.REQUEST_FAILING,
                                self._sm_nak_in_failed)
        self._sm.add_transition(states.RequesterStates.REQUEST_FAILING,
                                states.RequesterEvents.CANCEL_REQUESTED,
                                states.RequesterStates.REQUEST_FAILING,
                                self._sm_cancel_requested_when_closing)
        self._sm.add_transition(states.RequesterStates.REQUEST_FAILING,
                                states.RequesterEvents.CALLBACK_RETURNED,
                                states.RequesterStates.CLEANUP,
                                self._sm_failing_cb_returns)
        #  the next one is a super rare case where the timeout expires
        # but before it can get the lock the remote ends nacks
        # XXX TODO make its own CB
        self._sm.add_transition(states.RequesterStates.REQUEST_FAILING,
                                states.RequesterEvents.TIMEOUT,
                                states.RequesterStates.REQUEST_FAILING,
                                self._sm_requested_timeout)

        self._sm.add_transition(states.RequesterStates.ACK_SENT,
                                states.RequesterEvents.REPLY_RECEIVED,
                                states.RequesterStates.ACK_SENT,
                                self._sm_ack_sent_reply_received)
        self._sm.add_transition(states.RequesterStates.ACK_SENT,
                                states.RequesterEvents.CLEANUP_TIMEOUT,
                                states.RequesterStates.CLEANUP,
                                self._sm_ack_cleanup_timeout)
        self._sm.add_transition(states.RequesterStates.ACK_SENT,
                                states.RequesterEvents.NACK_RECEIVED,
                                states.RequesterStates.CLEANUP,
                                self._sm_failing_cb_returns)
        # again a timeout could theoretically happen in this state if the
        # timeout thread is quite slow at getting the lock
        self._sm.add_transition(states.RequesterStates.ACK_SENT,
                                states.RequesterEvents.TIMEOUT,
                                states.RequesterStates.ACK_SENT,
                                self._sm_requested_timeout)
