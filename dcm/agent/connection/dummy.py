import dcm.agent.connection.connection_interface as conniface


class DummyConnection(conniface.ConnectionInterface):

    def read(self):
        return None

    def send(self, doc):
        return None
