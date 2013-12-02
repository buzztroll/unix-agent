import logging

import dcm.agent.messaging.exceptions as exceptions
import dcm.agent.messaging.states as states
import dcm.agent.messaging.types as types
import dcm.agent.messaging.utils as utils


class ReplyRPC(object):

    def __init__(self, reply_listener, connection,
                 request_id, message_id, payload,
                 timeout=5):
        self._sm = states.StateMachine(states.ReplyStates.NEW)
        self._setup_states()
        self._sm.event_occurred(states.ReplyEvents.REQUEST_RECEIVED,
                                message={})
        self._request_id = request_id
        self._message_id = message_id
        self._request_payload = payload
        self._cancel_callback = None
        self._cancel_callback_args = None
        self._cancel_callback_kwargs = None
        self._done_callback = None
        self._done_callback_args = None
        self._done_callback_kwargs = None

        self._reply_message_timer = None
        self._reply_listener = reply_listener
        self._timeout = timeout
        self._conn = connection

    def ack(self,
            cancel_callback, cancel_callback_args, cancel_callback_kwargs,
            done_callback, done_callback_args, done_callback_kwargs):
        """
        Indicate to the messaging system that you have successfully received
        this message and stored it for processing.
        """
        self._cancel_callback = cancel_callback
        self._cancel_callback_args = cancel_callback_args
        if self._cancel_callback_args is None:
            self._cancel_callback_args = []
        self._cancel_callback_args.insert(0, self)
        self._cancel_callback_kwargs = cancel_callback_kwargs

        self._done_callback = done_callback
        self._done_callback_args = done_callback_args
        if self._done_callback_args is None:
            self._done_callback_args = []
        self._cancel_callback_args.insert(0, self)
        self._done_callback_kwargs = done_callback_kwargs

        self._sm.event_occurred(states.ReplyEvents.USER_ACCEPTS_REQUEST,
                                message={})

    def nak(self, response_document):
        """
        This function is called to out tight reject the message.  The user
        is signifying that this message will not be processed at all.
        A call to this function signifies that this object will no longer be
        referenced by the user.

        """
        self._sm.event_occurred(states.ReplyEvents.USER_REJECTS_REQUEST,
                                message=response_document)

    def reply(self, response_document):
        """
        Send a reply to this request.  This signifies that the user is
        done with this object.
        """
        self._sm.event_occurred(states.ReplyEvents.USER_REPLIES,
                                message=response_document)

    def reply_timeout(self, message_timer):
        self._sm.event_occurred(states.RequesterEvents.TIMEOUT,
                                message_timer=message_timer)

    def incoming_message(self, json_doc):
        type_to_event = {
            types.MessageTypes.ACK: states.ReplyEvents.REPLY_ACK_RECEIVED,
            types.MessageTypes.NACK: states.ReplyEvents.REPLY_NACK_RECEIVED,
            types.MessageTypes.REPLY: states.ReplyEvents.USER_REPLIES,
            types.MessageTypes.REQUEST: states.ReplyEvents.REQUEST_RECEIVED
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

    def _sm_initial_request_received(self, log, **kwargs):
        """
        This is the initial request, we simply set this to the requesting
        state.
        """
        pass

    def _sm_requesting_retransmission_received(self, log, **kwargs):
        """
        After receiving an initial request we receive a retransmission of it.
        The user has not yet acked the message but they have been notified
        that the message exists.  In this case we do nothing but wait for
        the user to ack the message
        """
        pass

    def _sm_requesting_cancel_received(self, log, **kwargs):
        """
        A cancel message flows over the wire after the request is received
        but before it is acknowledged.  Here we will tell the user about the
        cancel.  It is important that the cancel notification comes after
        the message received notification.
        """
        cb = states.UserCallback(logging,
                                self._cancel_callback,
                                self._cancel_callback_args,
                                self._cancel_callback_kwargs)
        self._reply_listener.register_user_callback(cb)

    def _sm_requesting_user_accepts(self, log, **kwargs):
        """
        The user decided to accept the message.  Here we will send the ack
        """
        ack_doc = {'type': types.MessageTypes.ACK,
                   'message_id': self._message_id,
                   'request_id': self._request_id}
        self._conn.send(ack_doc)

    def _sm_requesting_user_replies(self, log, **kwargs):
        """
        The user decides to reply before acknowledging the message.  Therefore
        we just send the reply and it acts as the ack and the reply
        """
        self._response_doc = kwargs['message']
        reply_doc = {'type': types.MessageTypes.REPLY,
                   'message_id': utils.new_message_id(),
                   'request_id': self._request_id,
                   'payload': self._response_doc}

        message_timer = utils.MessageTimer(self._timeout,
                                           self.reply_timeout,
                                           reply_doc)
        self._send_reply_message(message_timer)

    def _sm_requesting_user_rejects(self, log, **kwargs):
        """
        The user decides to reject the incoming request so we must send
        a nack to the remote side.
        """
        nack_doc = {'type': types.MessageTypes.NACK,
                    'message_id': self._message_id,
                    'request_id': self._request_id}
        self._conn.send(nack_doc)

    def _sm_acked_request_received(self, log, **kwargs):
        """
        In this case a retransmission of the request comes in after the user
        acknowledged the message.  Here we resend the ack.
        """
        # TODO verify the retransmission matches
        message = kwargs['message']

        # reply using the latest message id
        message_id = message['message_id']
        ack_doc = {'type': types.MessageTypes.ACK,
                   'message_id': message_id,
                   'request_id': self._request_id}
        self._conn.send(ack_doc)

    def _sm_acked_cancel_received(self, log, **kwargs):
        """
        A cancel is received from the remote end.  We simply notify the user
        of the request and allow the user to act upon it.
        """
        cb = states.UserCallback(logging,
                                self._cancel_callback,
                                self._cancel_callback_args,
                                self._cancel_callback_kwargs)
        self._reply_listener.register_user_callback(cb)

    def _sm_acked_reply(self, log, **kwargs):
        """
        This is the standard case.  A user has accepted the message and is
        now replying to it.  We send the reply.
        """
        self._response_doc = kwargs['message']
        reply_doc = {'type': types.MessageTypes.REPLY,
                   'message_id': utils.new_message_id(),
                   'request_id': self._request_id,
                   'payload': self._response_doc}

        message_timer = utils.MessageTimer(self._timeout,
                                           self.reply_timeout,
                                           reply_doc)
        self._send_reply_message(message_timer)

    def _sm_reply_request_retrans(self, log, **kwargs):
        """
        After replying to a message we receive a retransmission of the
        original request.  This can happen if the remote end never receives
        an ack and the reply message is either lost or delayed.  Here we
        retransmit the reply
        """
        reply_doc = {'type': types.MessageTypes.REPLY,
                   'message_id': utils.new_message_id(),
                   'request_id': self._request_id,
                   'payload': self._response_doc}
        self._conn.send(reply_doc)

    def _sm_reply_cancel_received(self, log, **kwargs):
        """
        This occurs when a cancel is received after a reply is sent.  It can
        happen if the remote end sends a cancel before the reply is received.
        Because we have already finished with this request we simply ignore
        this message.
        """
        pass

    def _sm_reply_ack_received(self, log, **kwargs):
        """
        This is the standard case.  A reply is sent and the ack to that
        reply is received.  At this point we know that the RPC was
        successful.
        """
        self._reply_message_timer.cancel()
        self._reply_message_timer = None
        self._reply_listener.message_done(self)

    def _sm_reply_ack_timeout(self, log, **kwargs):
        """
        This happens when after a given amount of time an ack has still not
        been received.  We thus must re-send the reply.
        """
        message_timer = kwargs['message_timer']
        # The time out did occur before the message could be acked so we must
        # resend it
        log.info("Resending reply id %s" % message_timer.message_id)
        self._send_reply_message(message_timer)

    def _sm_nacked_request_received(self, log, **kwargs):
        """
        This happens when a request is received after it has been nacked.
        This will occur if the first nack is lost or delayed.  We retransmit
        the nack
        """
        nack_doc = {'type': types.MessageTypes.NACK,
                    'message_id': self._message_id,
                    'request_id': self._request_id}
        self._conn.send(nack_doc)

    def _sm_nacked_timeout(self, log, **kwargs):
        """
        Once in the nack state we wait a while before terminating the
        communicate in case the nack is lost.  This happens when that waiting
        period has expired.
        """
        self._reply_listener.message_done(self)

    def _sm_cleanup_timeout(self, log, **kwargs):
        """
        This occurs if the timeout occurred while the reply ack was being
        processed but before the timer could be properly processed.  We
        can just ignore this.
        """
        pass

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
                                states.ReplyStates.REQUESTING,
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

        # note, eventually we will want to reply retrans logic to just punt
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.REPLY,
                                self._sm_reply_request_retrans)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.CANCEL_RECEIVED,
                                states.ReplyStates.REPLY,
                                self._sm_reply_cancel_received)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.REPLY_ACK_RECEIVED,
                                states.ReplyStates.CLEANUP,
                                self._sm_reply_ack_received)
        self._sm.add_transition(states.ReplyStates.REPLY,
                                states.ReplyEvents.TIMEOUT,
                                states.ReplyStates.REPLY,
                                self._sm_reply_ack_timeout)

        self._sm.add_transition(states.ReplyStates.NACKED,
                                states.ReplyEvents.REQUEST_RECEIVED,
                                states.ReplyStates.NACKED,
                                self._sm_nacked_request_received)
        self._sm.add_transition(states.ReplyStates.NACKED,
                                states.ReplyEvents.TIMEOUT,
                                states.ReplyStates.CLEANUP,
                                self._sm_nacked_timeout)

        self._sm.add_transition(states.ReplyStates.CLEANUP,
                                states.ReplyEvents.TIMEOUT,
                                states.ReplyStates.CLEANUP,
                                self._sm_cleanup_timeout)


class RequestListener(object):

    def __init__(self, connection,
                 request_callback,
                 request_callback_args,
                 request_callback_kwargs):
        self._conn = connection
        self._requests = {}
        self._request_callback_args = request_callback_args
        self._request_callback_kwargs = request_callback_kwargs
        self._request_callback = request_callback

    def _read(self):
        incoming_doc = self._conn.read()
        if incoming_doc['type'] == types.MessageTypes.REQUEST:
            # this is new request
            request_id = incoming_doc['request_id']
            if request_id in self._request_callback:
                # this is a retransmission, send in the message
                req = self._requests[request_id]
                req.incoming_message(incoming_doc)
                return
            message_id = incoming_doc['message_id']
            payload = incoming_doc['payload']
            msg = ReplyRPC(self, self._conn, request_id, message_id, payload)
            self._requests[request_id] = msg

            if self._request_callback:
                self._request_callback(*self._request_callback_args,
                                       **self._request_callback_kwargs)
            return msg
        else:
            request_id = incoming_doc['request_id']
            if request_id not in self._requests:
                # TODO send a NACK
                pass
            # get the message
            req = self._requests[request_id]
            req.incoming_message(incoming_doc)

    def poll(self):
        self._process_callbacks()
        return self._read()

    def message_done(self, reply_message):
        del self._requests[reply_message.get_request_id()]

    def register_user_callback(self, user_callback):
        self._user_callbacks_list.append(user_callback)

    def _process_callbacks(self):
        for cb in self._user_callbacks_list:
            cb.call()