import dcm.agent.utils as agent_util


class ConnectionInterface(object):

    @agent_util.not_implemented_decorator
    def set_receiver(self, receive_object):
        """
        Read 1 packet from the connection.  1 complete json doc.
        """
        pass

    @agent_util.not_implemented_decorator
    def send(self, doc):
        """
        Write a json document down the connection
        """
        pass

    @agent_util.not_implemented_decorator
    def connect(self):
        """
        establish a connection.  This will block until the handshake
        document returns.  Re-connections may happen after this which
        can be asynchronous but the first call must block until initial
        contact with estratius is made.
        """
        pass

    @agent_util.not_implemented_decorator
    def set_handshake(self, handshake_doc):
        """
        Set the handshake that will be sent out as part of connect.  This must
        be called before connect.
        """
        pass

    @agent_util.not_implemented_decorator
    def close(self):
        """
        Close the connection.  This gives implementations a chance to shutdown
        any associated threads
        """
        pass
