import logging
import threading
import time

import dcm.agent.exceptions as exceptions
import dcm.agent.messaging.states as states
import dcm.agent.messaging.types as types
import dcm.agent.messaging.utils as utils
import dcm.agent.util as agent_util
import dcm.eventlog.tracer as tracer


_g_logger = logging.getLogger(__name__)


class ReplyRPC(object):

    def __init__(self, agent_id, reply_listener, connection,
                 request_id, message_id, payload,
                 timeout=1.0):
        self._agent_id = agent_id
        self._request_id = request_id
        self._message_id = message_id
        self._request_payload = payload
        self._cancel_callback = None
        self._cancel_callback_args = None
        self._cancel_callback_kwargs = None

        self._reply_message_timer = None
        self._reply_listener = reply_listener
        self._timeout = timeout
        self._conn = connection

        self._lock = threading.RLock()

        self._sm = states.StateMachine(states.ReplyStates.NEW)
        self._setup_states()
        self._sm.event_occurred(states.ReplyEvents.REQUEST_RECEIVED,
                                message={})

    def get_request_id(self):
        return self._request_id

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def get_message_payload(self):
        return self._request_payload

    def kill(self):
        if self._reply_message_timer:
            try:
                self._reply_message_timer.cancel()
            except:
                # TODO LOG THIS
                pass

    @utils.class_method_sync()
    def ack(self,
            cancel_callback, cancel_callback_args, cancel_callback_kwargs):
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
        self._sm.event_occurred(states.ReplyEvents.USER_ACCEPTS_REQUEST,
                                message={})

    @utils.class_method_sync()
    def nak(self, response_document):
        """
        This function is called to out tight reject the message.  The user
        is signifying that this message will not be processed at all.
        A call to this function signifies that this object will no longer be
        referenced by the user.

        """
        self._sm.event_occurred(states.ReplyEvents.USER_REJECTS_REQUEST,
                                message=response_document)

    @utils.class_method_sync()
    def reply(self, response_document):
        """
        Send a reply to this request.  This signifies that the user is
        done with this object.
        """
        self._sm.event_occurred(states.ReplyEvents.USER_REPLIES,
                                message=response_document)

    @utils.class_method_sync()
    def reply_timeout(self, message_timer):
        self._sm.event_occurred(states.RequesterEvents.TIMEOUT,
                                message_timer=message_timer)

    @utils.class_method_sync()
    def incoming_message(self, json_doc):
        type_to_event = {
            types.MessageTypes.ACK: states.ReplyEvents.REPLY_ACK_RECEIVED,
            types.MessageTypes.NACK: states.ReplyEvents.REPLY_NACK_RECEIVED,
            types.MessageTypes.REPLY: states.ReplyEvents.USER_REPLIES,
            types.MessageTypes.CANCEL: states.ReplyEvents.CANCEL_RECEIVED,
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
        cb = states.UserCallback(self._cancel_callback,
                                 self._cancel_callback_args,
                                 self._cancel_callback_kwargs)
        self._reply_listener.register_user_callback(cb)

    def _sm_requesting_user_accepts(self, **kwargs):
        """
        The user decided to accept the message.  Here we will send the ack
        """
        ack_doc = {'type': types.MessageTypes.ACK,
                   'message_id': self._message_id,
                   'request_id': self._request_id}
        self._conn.send(ack_doc)

    def _sm_requesting_user_replies(self, **kwargs):
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

    def _sm_requesting_user_rejects(self, **kwargs):
        """
        The user decides to reject the incoming request so we must send
        a nack to the remote side.
        """
        nack_doc = {'type': types.MessageTypes.NACK,
                    'message_id': self._message_id,
                    'request_id': self._request_id,
                    'agent_id': self._agent_id}
        self._conn.send(nack_doc)

    def _sm_acked_request_received(self, **kwargs):
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

    def _sm_acked_cancel_received(self, **kwargs):
        """
        A cancel is received from the remote end.  We simply notify the user
        of the request and allow the user to act upon it.
        """
        cb = states.UserCallback(self._cancel_callback,
                                 self._cancel_callback_args,
                                 self._cancel_callback_kwargs)
        self._reply_listener.register_user_callback(cb)

    def _sm_acked_reply(self, **kwargs):
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

    def _sm_reply_request_retrans(self, **kwargs):
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
        self._reply_message_timer.cancel()
        self._reply_message_timer = None
        self._reply_listener.message_done(self)
        _g_logger.debug("Messaging complete.  State event transition: "
                        + str(self._sm.get_event_list()))

    def _sm_reply_ack_timeout(self, **kwargs):
        """
        This happens when after a given amount of time an ack has still not
        been received.  We thus must re-send the reply.
        """
        message_timer = kwargs['message_timer']
        # The time out did occur before the message could be acked so we must
        # resend it
        _g_logger.info("Resending reply id %s" % message_timer.message_id)
        self._send_reply_message(message_timer)

    def _sm_nacked_request_received(self, **kwargs):
        """
        This happens when a request is received after it has been nacked.
        This will occur if the first nack is lost or delayed.  We retransmit
        the nack
        """
        nack_doc = {'type': types.MessageTypes.NACK,
                    'message_id': self._message_id,
                    'request_id': self._request_id,
                    'agent_id': self._agent_id}
        self._conn.send(nack_doc)

    def _sm_nacked_timeout(self, **kwargs):
        """
        Once in the nack state we wait a while before terminating the
        communicate in case the nack is lost.  This happens when that waiting
        period has expired.
        """
        self._reply_listener.message_done(self)
        _g_logger.debug("NACK Ordered events: " +
                        str(self._sm.get_event_list()))

    def _sm_cleanup_timeout(self, **kwargs):
        """
        This occurs if the timeout occurred while the reply ack was being
        processed but before the timer could be properly processed.  We
        can just ignore this.
        """
        pass

    def _sm_cancel_waiting_ack(self, **kwargs):
        """
        If a cancel is received while in the requesting state we must make sure
        that the user does not get the cancel callback until after they have
        acked the message.  This handler occurs when the user calls ack()
        after a cancel has arrived.  Here we just register a cancel callback
        and let the user react to it how they will.
        """
        cb = states.UserCallback(self._cancel_callback,
                                 self._cancel_callback_args,
                                 self._cancel_callback_kwargs)
        self._reply_listener.register_user_callback(cb)

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

    def __init__(self, conf, connection, dispatcher):
        self._conn = connection
        self._dispatcher = dispatcher
        self._requests = {}
        self._expired_requests = {}
        self._messages_processed = 0
        self._user_callbacks_list = []
        self._reply_observers = []
        self._timeout = conf.messaging_retransmission_timeout
        self._shutdown = False
        self._conf = conf

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
                # dont let some crappy observer ruin everything
                pass

    def _process_doc(self, incoming_doc):
        if incoming_doc is None:
            return

        with tracer.RequestTracer(incoming_doc['request_id']):
            self._call_reply_observers("incoming_message", incoming_doc)
            _g_logger.debug("New message type %s" % incoming_doc['type'])

            if incoming_doc['type'] == types.MessageTypes.REQUEST:
                # this is new request
                request_id = incoming_doc['request_id']
                if request_id in self._expired_requests:
                    # this are old requests
                    nack_doc = {'type': types.MessageTypes.NACK,
                                'message_id': incoming_doc['message_id'],
                                'request_id': request_id,
                                'agent_id': self._conf.get_agent_id()}
                    self._conn.send(nack_doc)
                elif request_id in self._requests:
                    _g_logger.debug("Retransmission found")
                    # this is a retransmission, send in the message
                    req = self._requests[request_id]
                    req.incoming_message(incoming_doc)
                else:
                    if self._shutdown:
                        return
                    _g_logger.debug("New Request found")
                    message_id = incoming_doc['message_id']
                    payload = incoming_doc['payload']
                    msg = ReplyRPC(
                        self, self._conf.get_agent_id(),
                        self._conn, request_id, message_id, payload,
                        timeout=self._timeout)
                    self._dispatcher.incoming_request(msg)
                    self._call_reply_observers("new_message", msg)
                    # only add the message if processing was successful
                    self._requests[request_id] = msg
            else:
                request_id = incoming_doc['request_id']
                if request_id not in self._requests:
                    nack_doc = {'type': types.MessageTypes.NACK,
                                'message_id': incoming_doc['message_id'],
                                'request_id': request_id,
                                'agent_id': self._conf.get_agent_id()}
                    self._conn.send(nack_doc)
                else:
                    # get the message
                    req = self._requests[request_id]
                    req.incoming_message(incoming_doc)

    def _validate_doc(self, incoming_doc):
        pass

    def _send_bad_message_reply(self, incoming_doc, message):
        # we want to send a NACK to the message however it may be an error
        # because it was not formed with message_id or request_id.  In this
        # case we will send values in that place indicating that *a* message
        # was bad.  There will be almost no way for the sender to know which
        # one
        try:
            request_id = incoming_doc['request_id']
        except KeyError:
            request_id = "DEADBEEF"
        try:
            message_id = incoming_doc['message_id']
        except KeyError:
            message_id = "DEADBEEF"
        nack_doc = {'type': types.MessageTypes.NACK,
                    'message_id': message_id,
                    'request_id': request_id,
                    'error_message': message,
                    'agent_id': self._conf.get_agent_id()}
        self._conn.send(nack_doc)

    def poll(self):
        for cb in self._user_callbacks_list:
            with tracer.RequestTracer(cb.request_id):
                cb.call()
        incoming_doc = self._conn.recv()
        self._validate_doc(incoming_doc)

        try:
            self._process_doc(incoming_doc)
        except Exception as ex:
            _g_logger.warn("Error processing the message: " + str(incoming_doc),
                           ex)
            self._send_bad_message_reply(incoming_doc, ex.message)

        time.sleep(0)
        return self._shutdown and not self.is_busy()

    def message_done(self, reply_message):
        # we cannot drop this message too soon or retransmissions will cause
        # the command to be run again
        #
        #  TODO note thread safety

        # TODO put a soft state timer on the expired request IDs so that they
        # do not leak out forever
        request_id = reply_message.get_request_id()

        timer = threading.Timer(3600,
                                self._expired_req_timeout,
                                args=[request_id])
        self._expired_requests[request_id] = timer
        timer.start()

        del self._requests[request_id]
        self._messages_processed += 1
        self._call_reply_observers("message_done", reply_message)

    def _expired_req_timeout(self, req):
        # TODO note thread safety
        try:
            del self._expired_requests[req.get_request_id()]
        except:
            pass

    def register_user_callback(self, user_callback):
        self._user_callbacks_list.append(user_callback)

    def kill(self):
        for r_id in self._requests:
            reply = self._requests[r_id]
            reply.kill()

    def get_messages_processed(self):
        return self._messages_processed

    def is_busy(self):
        return len(self._requests) != 0

    def shutdown(self):
        """
        Stop accepting new requests but allow for outstanding messages to
        complete.
        """
        self._shutdown = True  # XXX danger will robinson.  Lets not have
                               # too many flags like this before we have
                               # a state machine
        for timer in self._expired_requests.values():
            timer.cancel()


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
