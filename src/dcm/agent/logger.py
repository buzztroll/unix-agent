#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import functools
import glob
import logging
from logging.handlers import RotatingFileHandler
import os
import urllib.parse
import urllib.error
import urllib.request
import pwd
import grp

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
                if isinstance(h, DCMAgentLogger):
                    h.clear_logs()


class DCMAgentLogger(RotatingFileHandler):

    def __init__(self, filename, owner=None, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        self._uid = pwd.getpwnam(owner).pw_uid
        self._gid = grp.getgrnam(owner).gr_gid
        super(DCMAgentLogger, self).__init__(
            filename, mode=mode, maxBytes=maxBytes, backupCount=backupCount,
            encoding=encoding, delay=delay)
        self.log_perms()

    def _open(self):
        s = super(DCMAgentLogger, self)._open()
        self.log_perms()
        return s

    def log_perms(self):
        for l in glob.glob("%s*" % os.path.abspath(self.baseFilename)):
            try:
                os.chown(l, self._uid, self._gid)
            except Exception:
                logging.exception("We could not set the log file ownership.")

    def clear_logs(self):
        with open(self.baseFilename, "w"):
            pass

        for l in glob.glob("%s.*" % self.baseFilename):
            try:
                os.remove(l)
            except:
                logging.exception("Failed to remove a rotated file.")


# Events to log to DCM
def log_to_dcm_console(level, base_message, msg=None, **kwargs):
    if not kwargs:
        out_message = base_message
    else:
        out_message = base_message % kwargs
    if msg:
        out_message = out_message + " : " + msg

    l_logger = logging.getLogger("dcm.agent.log.to.agent.manager")
    l_logger.log(level, out_message)


log_to_dcm_console_agent_started_log = functools.partial(
    log_to_dcm_console,
    logging.CRITICAL,
    "The agent has started.  Version %(version)s.")


log_to_dcm_console_successful_first_handshake = functools.partial(
    log_to_dcm_console,
    logging.CRITICAL,
    "The agent has connected.")


log_to_dcm_console_critical_error = functools.partial(
    log_to_dcm_console,
    logging.CRITICAL,
    "The agent experienced a critical error.")


log_to_dcm_console_overloaded = functools.partial(
    log_to_dcm_console,
    logging.CRITICAL,
    "The agent is overloaded.")


log_to_dcm_console_shutting_down = functools.partial(
    log_to_dcm_console,
    logging.CRITICAL,
    "The agent is shutting down.")


log_to_dcm_console_job_failed = functools.partial(
    log_to_dcm_console,
    logging.ERROR,
    "The job %(job_name)s failed with request_id %(request_id)s.")


log_to_dcm_console_unknown_job = functools.partial(
    log_to_dcm_console,
    logging.ERROR,
    "The job %(job_name)s is unknown.")


log_to_dcm_console_messaging_error = functools.partial(
    log_to_dcm_console,
    logging.ERROR,
    "The agent experienced a problem when communicating with DCM.")


log_to_dcm_console_unknown_job_parameter = functools.partial(
    log_to_dcm_console,
    logging.WARN,
    "The job %(job_name)s received the unknown parameter %(parameter_name)s.  The parameter will be ignored.")


log_to_dcm_console_successful_reconnect = functools.partial(
    log_to_dcm_console,
    logging.INFO,
    "The agent successfully reconnected.")


log_to_dcm_console_job_succeeded = functools.partial(
    log_to_dcm_console,
    logging.INFO,
    "The job %(job_name)s successfully completed with request_id %(request_id)s.")


log_to_dcm_console_job_started = functools.partial(
    log_to_dcm_console,
    logging.INFO,
    "The job %(job_name)s has started with request_id %(request_id)s.")


log_to_dcm_console_job_details = functools.partial(
    log_to_dcm_console,
    logging.DEBUG,
    "Details from %(job_name)s : %(details)s.")


log_to_dcm_console_incoming_message = functools.partial(
    log_to_dcm_console,
    logging.DEBUG,
    "An incoming message for the command %(job_name)s.")

