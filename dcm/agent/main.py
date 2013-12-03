import sys
import time

import dcm.agent.config as config
import dcm.agent.connection as connection
import dcm.agent.dispatcher as dispatcher


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


    while True:

        disp.incoming_message("echo", arguments=["poop face"])
        disp.incoming_message("cat", arguments=["/etc/group"])
        time.sleep(1)


main()