
class ConnectionInterface(object):

    def read(self):
        """
        Read 1 packet from the connection.  1 complete json doc.
        """
        pass

    def write(self, doc):
        """
        Write a json document down the connection
        """
        pass