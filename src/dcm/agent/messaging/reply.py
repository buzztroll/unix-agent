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
import threading
import signal
import sys

import dcm.agent.exceptions as exceptions
import dcm.agent.logger as dcm_logger
import dcm.agent.messaging.states as states
import dcm.agent.messaging.types as message_types
import dcm.agent.messaging.utils as utils
import dcm.agent.state_machine as state_machine
import dcm.agent.utils as agent_util
import dcm.eventlog.tracer as tracer

from dcm.agent.events.globals import global_space as dcm_events


_g_logger = logging.getLogger(__name__)


class ReplyRPC(object):

    MISSING_VALUE_STRING = "DEADBEEF"

    def __init__(self,
                 reply_listener,
                 agent_id,
                 connection,
                 request_id,
                 request_document,
                 db,
                 timeout=1.0,
                 reply_doc=None,
                 start_state=states.ReplyStates.REQUESTING):
        self._agent_id = agent_id
        self._request_id = request_id
        self._request_document = request_document
        self._cancel_callback = None
        self._cancel_callback_args = None
        self._cancel_callback_kwargs = None
        self._reply_message_timer = None
        self._reply_listener = reply_listener
        self._timeout = timeout
        self._conn = connection
        self._resend_reply_cnt = 0
        self._resend_reply_cnt_threshold = 5
        self._lock = threading.RLock()

        self._response_doc = reply_doc
        self._sm = state_machine.StateMachine(start_state)
        self._setup_states()
        self._db = db

    def get_request_id(self):
        return self._request_id

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def get_message_payload(self):
        return self._request_document["payload"]

    def shutdown(self):
        with tracer.RequestTracer(self._request_id):
            try:
                if self._reply_message_timer:
                    self._reply_message_timer.cancel()
                self._reply_listener.message_done(self)
            except Exception as ex:
                _g_logger.warn("Error shutting down the request", ex)

    def kill(self):
        with tracer.RequestTracer(self._request_id):
            if self._reply_message_timer:
                try:
                    self._reply_message_timer.cancel()
                except Exception as ex:
                    _g_logger.info("an exception occurred when trying to "
                                   "cancel the timer: " + str(ex))

    @agent_util.class_method_sync
    def ack(self,
            cancel_callback, cancel_callback_args, cancel_callback_kwargs):
        """
        Indicate to the messaging system that you have successfully received
        this message and stored it for processing.
        """
        with tracer.RequestTracer(self._request_id):
            self._cancel_callback = cancel_callback
            self._cancel_callback_args = cancel_callback_args

            if self._cancel_callback_args is None:
                self._cancel_callback_args = []
            self._cancel_callback_args.insert(0, self)
            self._cancel_callback_kwargs = cancel_callback_kwargs
            self._sm.event_occurred(states.ReplyEvents.USER_ACCEPTS_REQUEST,
                                    message={})

    @agent_util.class_method_sync
    def nak(self, response_document):
        """
        This function is called to out right reject the message.  The user
        is signifying that this message will not be processed at all.
        A call to this function signifies that this object will no longer be
        referenced by the user.

        """
        with tracer.RequestTracer(self._request_id):
            self._sm.event_occurred(states.ReplyEvents.USER_REJECTS_REQUEST,
                                    message=response_document)

    @agent_util.class_method_sync
    def reply(self, response_document):
        """
        Send a reply to this request.  This signifies that the user is
        done with this object.
        """
        with tracer.RequestTracer(self._request_id):
            _g_logger.debug("reply() has been called")
            self._sm.event_occurred(states.ReplyEvents.USER_REPLIES,
                                    message=response_document)

    @agent_util.class_method_sync
    def reply_timeout(self, message_timer):
        with tracer.RequestTracer(self._request_id):
            _g_logger.debug("reply timeout occurred, resending.")
            self._sm.event_occurred(states.RequesterEvents.TIMEOUT,
                                    message_timer=message_timer)

    @agent_util.class_method_sync
    def incoming_message(self, json_doc):
        with tracer.RequestTracer(self._request_id):
            type_to_event = {
                message_types.MessageTypes.ACK:
                    states.ReplyEvents.REPLY_ACK_RECEIVED,
                message_types.MessageTypes.NACK:
                states.ReplyEvents.REPLY_NACK_RECEIVED,
                message_types.MessageTypes.CANCEL:
                    states.ReplyEvents.CANCEL_RECEIVED,
                message_types.MessageTypes.STATUS:
                    states.ReplyEvents.STATUS_RECEIVED,
                message_types.MessageTypes.REQUEST:
                    states.ReplyEvents.REQUEST_RECEIVED
            }
            if 'type' not in json_doc:
                raise exceptions.MissingMessageParameterException('type')
            if json_doc['type'] not in type_to_event:
                raise exceptions.InvalidMessageParameterValueException(
                    'type', json_doc['type'])

            # this next call drives the state machine
            self._sm.event_occurred(type_to_event[json_doc['type']],
                                    message=json_doc)

    def _send_reply_message(self, message_timer):
        self._reply_message_timer = message_timer
        message_timer.send(self._conn)

    ###################################################################
    # state machine event handlers
    # ever method that starts with _sm_ is called under the same lock.
    ###################################################################

    def _sm_initial_request_received(self, **kwargs):
        """
        This is the initial request, we simply set this to the requesting
        state.
        """
        pass

    def _sm_requesting_retransmission_received(self, **kwargs):
        """
        After receiving an initial request we receive a retransmission of it.
        The user has not yet acked the message but they have been notified
        that the message exists.  In this case we do nothing but wait for
        the user to ack the message
        """
        pass

    def _sm_requesting_cancel_received(self, **kwargs):
        """
        A cancel message flows over the wire after the request is received
        but before it is acknowledged.  Here we will tell the user about the
        cancel.  It is important that the cancel notification comes after
        the message received notification.
        """
        dcm_events.register_callback(
            self._cancel_callback,
            args=self._cancel_callback_args,
            kwargs=self._cancel_callback_kwargs)

    def _sm_requesting_user_accepts(self, **kwargs):
        """
        The user decided to accept the message.  Here we will send the ack
        """
        self._db.new_record(self._request_id,
                            self._request_document,
                            None,
                            states.ReplyStates.ACKED,
                            self._agent_id)

        ack_doc = {'type': message_types.MessageTypes.ACK,
                   'message_id': utils.new_message_id(),
                   'request_id': self._request_id,
                   'entity': "user_accepts",
                   'agent_id': self._agent_id}
        self._conn.send(ack_doc)

    def _sm_requesting_user_replies(self, **kwargs):
        """
        The user decides to reply before acknowledging the message.  Therefore
        we just send the reply and it acts as the ack and the reply
        """
        self._response_doc = kwargs['message']

        self._db.update_record(self._request_id,
                               states.ReplyStates.REPLY,
                               reply_doc=self._response_doc)

        reply_doc = {'type': message_types.MessageTypes.REPLY,
                     'message_id': utils.new_message_id(),
                     'request_id': self._request_id,
                     'payload': self._response_doc,
                     'entity': "user_replies",
                     'agent_id': self._agent_id}

        message_timer = utils.MessageTimer(self._timeout,
                                           self.reply_timeout,
                                           reply_doc)
        self._send_reply_message(message_timer)

    def _sm_requesting_user_rejects(self, **kwargs):
        """
        The user decides to reject the incoming request so we must send
        a nack to the remote side.
        """
        self._db.new_record(self._request_id,
                            self._request_document,
                            None,
                            states.ReplyStates.ACKED,
                            self._agent_id)

        nack_doc = {'type': message_types.MessageTypes.NACK,
                    'message_id': utils.new_message_id(),
                    'request_id': self._request_id,
                    'entity': "user_rejects",
                    'error_message': "The agent rejected the request.",
                    'agent_id': self._agent_id}
        self._conn.send(nack_doc)

    def _sm_acked_request_received(self, **kwargs):
        """
        In this case a retransmission of the request comes in after the user
        acknowledged the message.  Here we resend the ack.
        """
        # reply using the latest message id
        ack_doc = {'type': message_types.MessageTypes.ACK,
                   'message_id': utils.new_message_id(),
                   'request_id': self._request_id,
                   'entity': "request_received",
                   'agent_id': self._agent_id}
        self._conn.send(ack_doc)

    def _sm_acked_cancel_received(self, **kwargs):
        """
        A cancel is received from the remote end.  We simply notify the user
        of the request and allow the user to act upon it.
        """
        dcm_events.register_callback(
            self._cancel_callback,
            args=self._cancel_callback_args,
            kwargs=self._cancel_callback_kwargs)

    def _sm_acked_reply(self, **kwargs):
        """
        This is the standard case.  A user has accepted the message and is
        now replying to it.  We send the reply.
        """
        self._response_doc = kwargs['message']

        self._db.update_record(self._request_id,
                               states.ReplyStates.REPLY,
                               reply_doc=self._response_doc)

        reply_doc = {'type': message_types.MessageTypes.REPLY,
                     'message_id': utils.new_message_id(),
                     'request_id': self._request_id,
                     'payload': self._response_doc,
                     'entity': "acked_reply",
                     'agent_id': self._agent_id}

        message_timer = utils.MessageTimer(self._timeout,
                                           self.reply_timeout,
                                           reply_doc)
        self._send_reply_message(message_timer)

    def _sm_acked_re_reply(self, **kwargs):
        self._db.update_record(self._request_id,
                               states.ReplyStates.REPLY,
                               reply_doc=self._response_doc)

        reply_doc = {'type': message_types.MessageTypes.REPLY,
                     'message_id': utils.new_message_id(),
                     'request_id': self._request_id,
                     'payload': self._response_doc,
                     'entity': "acked_reply",
                     'agent_id': self._agent_id}

        message_timer = utils.MessageTimer(self._timeout,
                                           self.reply_timeout,
                                           reply_doc)
        self._send_reply_message(message_timer)

    def _sm_reply_request_retrans(self, **kwargs):
        """
        After replying to a message we receive a retransmission of the
        original request.  This can happen if the remote end never receives
        an ack and the reply message is either lost or delayed.  Here we
        retransmit the reply.
        """
        reply_doc = {'type': message_types.MessageTypes.REPLY,
                     'message_id': utils.new_message_id(),
                     'request_id': self._request_id,
                     'payload': self._response_doc,
                     'entity': "request_retrans",
                     'agent_id': self._agent_id}

        message_timer = utils.MessageTimer(self._timeout,
                                           self.reply_timeout,
                                           reply_doc)
        self._send_reply_message(message_timer)

    def _sm_reply_cancel_received(self, **kwargs):
        """
        This occurs when a cancel is received after a reply is sent.  It can
        happen if the remote end sends a cancel before the reply is received.
        Because we have already finished with this request we simply ignore
        this message.
        """
        pass

    def _sm_reply_ack_received(self, **kwargs):
        """
        This is the standard case.  A reply is sent and the ack to that
        reply is received.  At this point we know that the RPC was
        successful.
        """
        self._db.update_record(self._request_id,
                               states.ReplyStates.REPLY_ACKED)
        self._reply_message_timer.cancel()
        self._reply_message_timer = None
        self._reply_listener.message_done(self)
        _g_logger.debug("Messaging complete.  State event transition: "
                        + str(self._sm.get_event_list()))

    def _sm_reply_nack_received(self, **kwargs):
        """
        The reply was nacked.  This is probably a result of the a
        retransmission that was not needed.
        """
        self._db.update_record(self._request_id,
                               states.ReplyStates.REPLY_NACKED)

        self._reply_message_timer.cancel()
        self._reply_message_timer = None
        self._reply_listener.message_done(self)
        _g_logger.debug("Reply NACKed, messaging complete.  State event "
                        "transition: " + str(self._sm.get_event_list()))

    def _sm_reply_ack_timeout(self, **kwargs):
        """
        This happens when after a given amount of time an ack has still not
        been received.  We thus must re-send the reply.
        """
        message_timer = kwargs['message_timer']
        # The time out did occur before the message could be acked so we must
        # resend it
        _g_logger.info("Resending reply")
        self._resend_reply_cnt += 1
        if self._resend_reply_cnt > self._resend_reply_cnt_threshold:
            # TODO punt at some point ?
            pass
        self._send_reply_message(message_timer)

    def _sm_nacked_request_received(self, **kwargs):
        """
        This happens when a request is received after it has been nacked.
        This will occur if the first nack is lost or delayed.  We retransmit
        the nack
        """
        nack_doc = {'type': message_types.MessageTypes.NACK,
                    'message_id': utils.new_message_id(),
                    'request_id': self._request_id,
                    'entity': "request_received",
                    'error_message': "The agent already rejected this request",
                    'agent_id': self._agent_id}
        self._conn.send(nack_doc)

    def _sm_cancel_waiting_ack(self, **kwargs):
        """
        If a cancel is received while in the requesting state we must make sure
        that the user does not get the cancel callback until after they have
        acked the message.  This handler occurs when the user calls ack()
        after a cancel has arrived.  Here we just register a cancel callback
        and let the user react to it how they will.
        """
        dcm_events.register_user_callback(
            self._cancel_callback,
            args=self._cancel_callback_args,
            kwargs=self._cancel_callback_kwargs)

    def _sm_send_status(self):
        status_doc = {'type': message_types.MessageTypes.STATUS,
                      'message_id': utils.new_message_id(),
                      'request_id': self._request_id,
                      'entity': "status send",
                      'agent_id': self._agent_id,
                      'state': self._sm._current_state,
                      'reply': self._response_doc}
        self._conn.send(status_doc)

    def _sm_reinflated_reply_ack(self):
        _g_logger.warn("The agent manager sent a message for this request "
                       "after it was in the REPLY_ACK state")

    def _sm_reinflated_reply_nack(self):
        _g_logger.warn("The agent manager sent a message for this request "
                       "after it was in the REPLY_NACK state")

    def _reinflate_done(self):
        if self._reply_message_timer:
            self._reply_message_timer.cancel()
            self._reply_message_timer = None
        self._reply_listener.message_done(self)

    def _sm_reply_ack_re_acked(self, message=None):
        """
        This is called when a re-inflated state had already been reply acked,
        and is now acked again.  We just take it out of memory.
        """
        self._reinflate_done()

    def _sm_reply_ack_now_nacked(self, message=None):
        """
        This is called whenever a re-inflated command reaches a terminal state
        that was
        """
        self._reinflate_done()

    def _sm_reply_nack_re_nacked(self, message=None):
        """
        This is called when a re-inflated state had already been reply nacked,
        and is now nacked again.  We just take it out of memory.
        """
        self._reinflate_done()

    def _sm_reply_nack_now_acked(self, message=None):
        """
        This is called whenever a re-inflated command reaches acked state but
        it was previously nacked
        """
        self._reinflate_done()

    def _sm_ack_reply_nack_received(self, message=None):
        _g_logger.warn("A NACK was received when in the ACK state "
                       + str(message))
        # this will be cleaned up when the command replies, which it is
        # required to do

    def _sm_replied_nacked_reply(self, message=None):
        """
        This is called when a request was received but the ACK for that
        request received a NACK.  However the command finished running
        and a reply was sent back.  Here we cancel the message and log the
        event
        """
        _g_logger.warn("A command that was already finished ended "
                       + str(message))
        self.shutdown()

    def _setup_states(self):
        self._sm.add_transition(states.ReplyStates.NEW,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.REQUESTING,
                                self._sm_initial_request_received)

        self._sm.add_transition(states.ReplyStates.REQUESTING,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.REQUESTING,
                                self._sm_requesting_retransmission_received)
        self._sm.add_transition(states.ReplyStates.REQUESTING,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                self._sm_requesting_cancel_received)
        self._sm.add_transition(states.ReplyStates.REQUESTING,
                                states.ReplyEvents.USER_ACCEPTS_REQUEST,
                                states.ReplyStates.ACKED,
                                self._sm_requesting_user_accepts)
        self._sm.add_transition(states.ReplyStates.REQUESTING,
                                states.ReplyEvents.USER_REPLIES,
                                states.ReplyStates.REPLY,
                                self._sm_requesting_user_replies)
        self._sm.add_transition(states.ReplyStates.REQUESTING,
                                states.ReplyEvents.USER_REJECTS_REQUEST,
                                states.ReplyStates.NACKED,
                                self._sm_requesting_user_rejects)
        self._sm.add_transition(states.ReplyStates.REQUESTING,
                                states.ReplyEvents.STATUS_RECEIVED,
                                states.ReplyStates.REQUESTING,
                                self._sm_send_status)

        self._sm.add_transition(states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                self._sm_requesting_retransmission_received)
        self._sm.add_transition(states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                None)
        self._sm.add_transition(states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                states.ReplyEvents.USER_ACCEPTS_REQUEST,
                                states.ReplyStates.ACKED,
                                self._sm_cancel_waiting_ack)
        self._sm.add_transition(states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                states.ReplyEvents.USER_REPLIES,
                                states.ReplyStates.REPLY,
                                self._sm_requesting_user_replies)
        self._sm.add_transition(states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                states.ReplyEvents.USER_REJECTS_REQUEST,
                                states.ReplyStates.NACKED,
                                self._sm_requesting_user_rejects)
        self._sm.add_transition(states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                states.ReplyEvents.STATUS_RECEIVED,
                                states.ReplyStates.CANCEL_RECEIVED_REQUESTING,
                                self._sm_send_status)

        self._sm.add_transition(states.ReplyStates.ACKED,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.ACKED,
                                self._sm_acked_request_received)
        self._sm.add_transition(states.ReplyStates.ACKED,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.ACKED,
                                self._sm_acked_cancel_received)
        self._sm.add_transition(states.ReplyStates.ACKED,
                                states.ReplyEvents.USER_REPLIES,
                                states.ReplyStates.REPLY,
                                self._sm_acked_reply)
        self._sm.add_transition(states.ReplyStates.ACKED,
                                states.ReplyEvents.STATUS_RECEIVED,
                                states.ReplyStates.ACKED,
                                self._sm_send_status)

        # if the AM receives and ACK but has never heard of the request ID
        # it will send a nack.  this should not happen in a normal course
        # of events.  At this point we should just kill the request and
        # log a scary message.  We also need to kill anything running for that
        # that request
        # This will happen when the agent manager quits on a request before
        # the agent sends the ack.  when the AM receives the ack it has already
        # canceled the request and thus NACKs the ACK
        self._sm.add_transition(states.ReplyStates.ACKED,
                                states.ReplyEvents.REPLY_NACK_RECEIVED,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_ack_reply_nack_received)

        # note, eventually we will want to reply retrans logic to just punt
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.REPLY,
                                self._sm_reply_request_retrans)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.USER_REPLIES,
                                states.ReplyStates.REPLY,
                                self._sm_acked_reply)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.REPLY,
                                self._sm_reply_cancel_received)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.REPLY_ACK_RECEIVED,
                                states.ReplyStates.REPLY_ACKED,
                                self._sm_reply_ack_received)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.TIMEOUT,
                                states.ReplyStates.REPLY,
                                self._sm_reply_ack_timeout)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.REPLY_NACK_RECEIVED,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_reply_nack_received)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.STATUS_RECEIVED,
                                states.ReplyStates.REPLY,
                                self._sm_send_status)

        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.DB_INFLATE,
                                states.ReplyStates.REPLY,
                                self._sm_acked_re_reply)

        self._sm.add_transition(states.ReplyStates.NACKED,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.NACKED,
                                self._sm_nacked_request_received)
        self._sm.add_transition(states.ReplyStates.NACKED,
                                states.ReplyEvents.STATUS_RECEIVED,
                                states.ReplyStates.NACKED,
                                self._sm_send_status)

        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.REPLY_ACKED,
                                self._sm_reply_request_retrans)
        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.REPLY_ACK_RECEIVED,
                                states.ReplyStates.REPLY_ACKED,
                                self._sm_reply_ack_re_acked)
        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.REPLY_NACK_RECEIVED,
                                states.ReplyStates.REPLY_ACKED,
                                self._sm_reply_ack_now_nacked)
        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.REPLY_ACKED,
                                None)
        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.STATUS_RECEIVED,
                                states.ReplyStates.REPLY_ACKED,
                                self._sm_send_status)
        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.TIMEOUT,
                                states.ReplyStates.REPLY_ACKED,
                                None)

        # this transition should only occur when the AM makes a mistake
        # or messages are received out of order.
        self._sm.add_transition(states.ReplyStates.REPLY_ACKED,
                                states.ReplyEvents.DB_INFLATE,
                                states.ReplyStates.REPLY_ACKED,
                                self._sm_reinflated_reply_ack)

        self._sm.add_transition(states.ReplyStates.REPLY_NACKED,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_reply_request_retrans)
        self._sm.add_transition(states.ReplyStates.REPLY_NACKED,
                                states.ReplyEvents.REPLY_ACK_RECEIVED,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_reply_nack_re_nacked)
        self._sm.add_transition(states.ReplyStates.REPLY_NACKED,
                                states.ReplyEvents.REPLY_NACK_RECEIVED,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_reply_nack_now_acked)
        self._sm.add_transition(states.ReplyStates.REPLY_NACKED,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.REPLY_NACKED,
                                None)

        # this will happen when the plugin finishes and thus replies
        # to a request that had its ACK NACKed.  In this case we
        # just cancel the messaging and log a message
        self._sm.add_transition(states.ReplyStates.REPLY_NACKED,
                                states.ReplyEvents.USER_REPLIES,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_replied_nacked_reply)

        # this next state should only occur when a message is out
        # of order or the agent manager made a mistake
        self._sm.add_transition(states.ReplyStates.REPLY_NACKED,
                                states.ReplyEvents.DB_INFLATE,
                                states.ReplyStates.REPLY_NACKED,
                                self._sm_reinflated_reply_ack)


class RequestListener(object):

    def __init__(self, conf, sender_connection, dispatcher,
                 db, id_system=None):
        self._conn = sender_connection
        self._dispatcher = dispatcher
        self._requests = {}
        self._messages_processed = 0

        self._reply_observers = []
        self._timeout = conf.messaging_retransmission_timeout
        self._shutdown = False
        self._conf = conf
        self._db = db
        self._id_system = id_system
        self._lock = threading.RLock()
        self._db.starting_agent()

    def get_reply_observers(self):
        # get the whole list so that the user can add and remove themselves.
        # This sort of thing should be done only with carefully writen code
        # using carefully writen observers that do very light weight
        # nonblocking operations
        return self._reply_observers

    def _call_reply_observers(self, func_name, argument):
        for o in self._reply_observers:
            try:
                func = getattr(o, func_name)
                func(argument)
            except:
                _g_logger.exception("A bad observer threw an exception.")
                # dont let some crappy observer ruin everything
                pass

    def _process_doc(self, incoming_doc):
        if incoming_doc is None:
            return

        with tracer.RequestTracer(incoming_doc['request_id']):
            self._call_reply_observers("incoming_message", incoming_doc)
            _g_logger.debug("New message type %s" % incoming_doc['type'])

            # if the agent is misbehaving the AM might tell it to kill itself.
            # cold.
            if incoming_doc["type"] == message_types.MessageTypes.HEMLOCK:
                _g_logger.error("HEMLOCK: DCM told me to kill myself.")
                os.killpg(0, signal.SIGKILL)
                sys.exit(10)

            # if it is a alert message short circuit
            if incoming_doc["type"] == message_types.MessageTypes.ALERT_ACK:
                if self._id_system:
                    self._id_system.incoming_message(incoming_doc)
                return

            request_id = incoming_doc["request_id"]

            # is this request already in memory?
            if request_id in self._requests:
                _g_logger.debug("The message was found in the requests.")

                # send it through, state machine will deal with it
                req = self._requests[request_id]
                req.incoming_message(incoming_doc)
                return
            # if the request id has already been seen by the database
            db_record = self._db.lookup_req(request_id)
            if db_record:
                _g_logger.info("Inflating the record from the DB."
                               + request_id)
                req = ReplyRPC(
                    self,
                    self._conf.agent_id,
                    self._conn,
                    request_id,
                    incoming_doc,
                    self._db,
                    timeout=self._timeout,
                    reply_doc=db_record.reply_doc,
                    start_state=db_record.state)

                # this will probably be used in the near future so get it
                # on the memory list
                self._requests[request_id] = req
                req.incoming_message(incoming_doc)
                return

            if incoming_doc["type"] == message_types.MessageTypes.REQUEST:
                if len(list(self._requests.keys())) >=\
                        self._conf.messaging_max_at_once > -1:

                    # short circuit the case where the agent is too busy
                    dcm_logger.log_to_dcm_console_overloaded(
                        msg="The new request was rejected because the agent has too many outstanding requests.")
                    nack_doc = {
                        'type': message_types.MessageTypes.NACK,
                        'message_id': utils.new_message_id(),
                        'request_id': request_id,
                        'agent_id': self._conf.agent_id,
                        'error_message': ("The agent can only handle %d "
                                          "commands at once"
                                          % self._conf.messaging_max_at_once)}
                    self._conn.send(nack_doc)
                    return

                _g_logger.debug("A new request has come in.")

                req = ReplyRPC(
                    self,
                    self._conf.agent_id,
                    self._conn,
                    request_id,
                    incoming_doc,
                    self._db,
                    timeout=self._timeout)
                self._call_reply_observers("new_message", req)

                # only add the message if processing was successful
                self._requests[request_id] = req
                try:
                    self._dispatcher.incoming_request(req)
                except Exception:
                    _g_logger.exception("The dispatcher could not handle a "
                                        "message.")
                    del self._requests[request_id]
                    dcm_logger.log_to_dcm_console_messaging_error(
                        msg="The dispatcher could not handle the message.")
                    raise
            else:
                # if we have never heard of the ID and this is not a new
                # request we return a courtesy error
                _g_logger.debug("Unknown message ID sending a NACK")

                nack_doc = {'type': message_types.MessageTypes.NACK,
                            'message_id': utils.new_message_id(),
                            'request_id': request_id,
                            'agent_id': self._conf.agent_id,
                            'error_message':
                            "%s is an unknown ID" % request_id}
                self._conn.send(nack_doc)

    def _validate_doc(self, incoming_doc):
        pass

    def _send_bad_message_reply(self, incoming_doc, message):
        _g_logger.debug("Sending the bad message %s" % message)
        # we want to send a NACK to the message however it may be an error
        # because it was not formed with message_id or request_id.  In this
        # case we will send values in that place indicating that *a* message
        # was bad.  There will be almost no way for the sender to know which
        # one
        try:
            request_id = incoming_doc['request_id']
        except KeyError:
            request_id = ReplyRPC.MISSING_VALUE_STRING

        nack_doc = {'type': message_types.MessageTypes.NACK,
                    'message_id': utils.new_message_id(),
                    'request_id': request_id,
                    'error_message': message,
                    'agent_id': self._conf.agent_id}
        self._conn.send(nack_doc)

    def message_done(self, reply_message):
        self._lock.acquire()
        try:
            request_id = reply_message.get_request_id()
            del self._requests[request_id]
            _g_logger.debug("The message %s has completed and is being "
                            "removed" % request_id)
            self._messages_processed += 1
        finally:
            self._lock.release()
        self._call_reply_observers("message_done", reply_message)

    def get_messages_processed(self):
        return self._messages_processed

    def is_busy(self):
        return len(self._requests) != 0

    def shutdown(self):
        """
        Stop accepting new requests but allow for outstanding messages to
        complete.
        """
        self._shutdown = True  #  XXX danger will robinson.  Lets not have
                               #  too many flags like this before we have
                               #  a state machine
        for req in list(self._requests.values()):
            req.kill()

    def wait_for_all_nicely(self):
        # XXX TODO how long should this block? do we need this?  looks like just for tests
        while self._requests:
            dcm_events.poll()

    def reply(self, request_id, reply_doc):
        reply_req = self._requests[request_id]
        reply_req.reply(reply_doc)

    def incoming_parent_q_message(self, incoming_doc):
        _g_logger.debug("Received message %s" % str(incoming_doc))
        try:
            self._validate_doc(incoming_doc)
            self._process_doc(incoming_doc)
        except Exception as ex:
            _g_logger.exception(
                "Error processing the message: %s" % str(incoming_doc))
            self._send_bad_message_reply(incoming_doc, str(ex))


class ReplyObserverInterface(object):
    @agent_util.not_implemented_decorator
    def new_message(self, reply):
        pass

    @agent_util.not_implemented_decorator
    def message_done(self, reply):
        pass

    @agent_util.not_implemented_decorator
    def incoming_message(self, incoming_doc):
        pass
