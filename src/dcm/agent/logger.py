import logging
from dcm.agent import parent_receive_q


def send_log_to_dcm_callback(conn=None, message=None):
    msg = {
        "type": "LOG",
        "message": message
    }
    conn.send(msg)


class dcmLogger(logging.Handler):

    def __init__(self, encoding=None):
        super(dcmLogger, self).__init__()
        self._conn = None
        self._unsent_msgs = []

    def emit(self, record):
        msg = self.format(record)
        if self._conn is None:
            self._unsent_msgs.append(msg)
        else:
           parent_receive_q.register_user_callback(
                send_log_to_dcm_callback, kwargs={"conn": self._conn,
                                                  "message": msg})

    def set_conn(self, conn):
        self._conn = conn

        for msg in self._unsent_msgs:
           parent_receive_q.register_user_callback(
                send_log_to_dcm_callback, kwargs={"conn": self._conn,
                                                  "message": msg})
           self._unsent_msgs = []


def set_dcm_connection(conn):
    for key in logging.Logger.manager.loggerDict:
        logger = logging.Logger.manager.loggerDict[key]
        if type(logger) == logging.Logger:
            for h in logger.handlers:
                if type(h) == dcmLogger:
                    h.set_conn(conn)


def clear_dcm_logging():
    # effectively just for tests
    for key in logging.Logger.manager.loggerDict:
        logger = logging.Logger.manager.loggerDict[key]
        if type(logger) == logging.Logger:
            for h in logger.handlers:
                if type(h) == dcmLogger:
                    h.set_conn(None)
