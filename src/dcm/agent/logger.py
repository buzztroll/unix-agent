import logging


class dcmLogger(logging.Handler):
    _conn = None

    def __init__(self, encoding=None):
        super(dcmLogger, self).__init__()

    def emit(self, record):
        if self._conn is None:
            return
        msg = self.format(record)
        self._conn.log(msg)

    def set_conn(self, conn):
        self._conn = conn


def set_dcm_connection(conn):
    for key in logging.Logger.manager.loggerDict:
        logger = logging.Logger.manager.loggerDict[key]
        if type(logger) == logging.Logger:
            for h in logger.handlers:
                if type(h) == dcmLogger:
                    h.set_conn(conn)