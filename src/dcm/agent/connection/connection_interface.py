import dcm.agent.utils as agent_util


class ConnectionInterface(object):

    @agent_util.not_implemented_decorator
    def send(self, doc):
        """
        Write a json document down the connection
        """
        pass

    @agent_util.not_implemented_decorator
    def connect(self, receive_object, handshake_manager):
        """
        Start the connection object.  The incoming data will be sent to the
        receive_object which should implement ParentReceiveQObserver.  In
        response to the connection the agent manager will send a handshake
        document.
        """
        pass

    @agent_util.not_implemented_decorator
    def close(self):
        """
        Close the connection.  This gives implementations a chance to shutdown
        any associated threads
        """
        pass
