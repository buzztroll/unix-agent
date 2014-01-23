import uuid
import dcm.agent.connection.connection_interface as conniface


class DummyConnection(conniface.ConnectionInterface):

    def connect(self):
        return {"return_code": 200, "agent_id": str(uuid.uuid4())}

    def recv(self):
        return None

    def send(self, doc):
        return None

    def set_handshake(self, handshake_doc):
        pass
