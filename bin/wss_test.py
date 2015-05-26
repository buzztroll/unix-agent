import json
import logging
import sys
import time
import ws4py.client.threadedclient as ws4py_client


_g_logger = logging.getLogger(__name__)


class TestWebSocketClient(ws4py_client.WebSocketClient):

    def __init__(self, url):
        ws4py_client.WebSocketClient.__init__(self, url)
        self._url = url
        self.done = False

    def opened(self):
        print("open")
        _g_logger.debug("Web socket %s has been opened" % self._url)

    def closed(self, code, reason=None):
        print("closed " + str(code) + ":" + str(reason))
        _g_logger.info("Web socket %s has been closed %d %s"
                       % (self._url, code, reason))
        self.done = True

    def received_message(self, m):
        print(str(m.data))
        _g_logger.debug("WS message received " + m.data)


def main(argv=sys.argv):
    ws = TestWebSocketClient(argv[1])
    ws.connect()

    fake_hs = {
        'ipv4': ["127.0.0.1"],
        'ipv6': [],
        'agent_id': "not-real",
        'token': "deadbeef",
        'vm_instance': "deadbeef",
        'injected_id': "deadbeef",
        'version': "101",
        'protocol_version': "101",
        'platform': "ubuntu"
        }

    ws.send(json.dumps(fake_hs))
    while not ws.done:
        time.sleep(0.1)


if __name__ == '__main__':
    main()
