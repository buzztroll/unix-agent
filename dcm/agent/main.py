import time

import dcm.agent.config as config
import dcm.agent.connection as connection
import dcm.agent.dispatcher as dispatcher
import dcm.agent.messaging.reply as reply


def main():

    # def setup config object
    conf_object = config.AgentConfig()
    conf_object.setup()

    # def get a connection object
    conn = connection.get_connection_object(conf_object)

    disp = dispatcher.Dispatcher(conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(
        conn, None, None, None)

    # todo drive this loop with something real
    while True:
        msg = request_listener.poll()
        if msg is not None:
            disp.incoming_request(msg)
        time.sleep(1)


main()