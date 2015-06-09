import glob
import logging
from logging.handlers import RotatingFileHandler
import os
import urllib.parse
import urllib.error
import urllib.request

from dcm.agent.events.globals import global_space as dcm_events


def send_log_to_dcm_callback(conn=None, token=None, message=None, level=None):
    max_size = 10*1024
    if len(message) > max_size:
        message = message[:max_size]
    message = urllib.parse.quote(message)
    msg = {
        "type": "LOG",
        "token": token,
        "level": level,
        "message": message
    }
    conn.send(msg)


class dcmLogger(logging.Handler):

    def __init__(self, encoding=None):
        super(dcmLogger, self).__init__()
        self._conn = None
        self._conf = None
        self._unsent_msgs = []

    def emit(self, record):
        msg = self.format(record)
        if self._conn is None:
            self._unsent_msgs.append(msg)
        else:
            dcm_events.register_callback(
                send_log_to_dcm_callback, kwargs={"conn": self._conn,
                                                  "token": "",
                                                  "message": msg,
                                                  "level": record.levelname})

    def set_conn(self, conf, conn):
        self._conn = conn
        self._conf = conf
        if conn is None:
            return
        for msg in self._unsent_msgs:
            dcm_events.register_callback(
                send_log_to_dcm_callback, kwargs={"conn": self._conn,
                                                  "message": msg})
            self._unsent_msgs = []


def set_dcm_connection(conf, conn):
    for key in logging.Logger.manager.loggerDict:
        logger = logging.Logger.manager.loggerDict[key]
        if type(logger) == logging.Logger:
            for h in logger.handlers:
                if type(h) == dcmLogger:
                    h.set_conn(conf, conn)


def clear_dcm_logging():
    # effectively just for tests
    for key in logging.Logger.manager.loggerDict:
        logger = logging.Logger.manager.loggerDict[key]
        if type(logger) == logging.Logger:
            for h in logger.handlers:
                if type(h) == dcmLogger:
                    h.set_conn(None, None)


def delete_logs():
    # effectively just for tests
    for key in logging.Logger.manager.loggerDict:
        logger = logging.Logger.manager.loggerDict[key]
        if type(logger) == logging.Logger:
            for h in logger.handlers:
                if isinstance(h, logging.FileHandler):
                    # just to truncate the file
                    with open(h.baseFilename, "w"):
                        pass

                    if isinstance(h, RotatingFileHandler):
                        for l in glob.glob("%s.*" % h.baseFilename):
                            try:
                                os.remove(l)
                            except:
                                pass
