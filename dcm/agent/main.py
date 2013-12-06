import time
from dcm.agent import exceptions

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.messaging.reply as reply


def main():

    # def setup config object
    conf_object = config.AgentConfig()
    conf_object.setup()

    # def get a connection object
    conn = config.get_connection_object(conf_object)

    disp = dispatcher.Dispatcher(conf_object)
    disp.start_workers()

    request_listener = reply.RequestListener(
        conn, None, None, None)

    # todo drive this loop with something real
    done = False
    while True:
        try:
            if done and not request_listener.is_busy():
                break
            msg = request_listener.poll()
            if msg is not None:
                disp.incoming_request(msg)
        except exceptions.PerminateConnectionException:
            done = True
            time.sleep(1)
        except Exception as ex:
            raise

    disp.stop()


main()
