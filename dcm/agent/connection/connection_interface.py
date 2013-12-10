import dcm.agent.util as agent_util

class ConnectionInterface(object):

    @agent_util.not_implemented_decorator
    def read(self):
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
