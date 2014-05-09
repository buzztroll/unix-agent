import dcm.agent.utils as agent_util


class HandshakeReceiverInterface(object):
    """
    This is the interface that shows what methods will be called on the
    connection receiving object
    """
    @agent_util.not_implemented_decorator
    def incoming_handshake(self, connection, handshake_doc):
        pass


class ConnectionInterface(object):

    @agent_util.not_implemented_decorator
    def send(self, doc):
        """
        Write a json document down the connection
        """
        pass

    @agent_util.not_implemented_decorator
    def connect(self, receive_object, incoming_handshake_object, outgoing_handshake_doc):
        """
        Start the connection object.  The incoming data will be sent to the
        receive_object which should implement ParentReceiveQObserver.  In
        response to the connection the agent manager will send a handshake
        document.  When this happens methods on incoming_handshake_object
        will be called.  It can be called more than once but the data should
        always be the same.
        """
        pass

    @agent_util.not_implemented_decorator
    def close(self):
        """
        Close the connection.  This gives implementations a chance to shutdown
        any associated threads
        """
        pass
