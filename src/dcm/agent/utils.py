#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================

import os
import tempfile
import sys
import exceptions
import logging
import random
import string
import subprocess


_g_logger = logging.getLogger(__name__)


class OperationalState(object):
    OK = "OK"
    EXCESS_RESOURCES = "EXCESS_RESOURCES"
    CONSTRAINED_RESOURCES = "CONSTRAINED_RESOURCES"
    TERMINATED = "TERMINATED"
    NOT_RESPONDING = "NOT_RESPONDING"
    AGENT_FAILURE = "AGENT_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"


class JobLogHandler(logging.FileHandler):

    def __init__(self, filename_format="%(logname)s.log", mode='a',
                 encoding=None):
        self.filename_format = filename_format
        self.file_handles = {}
        base_filename = 'jobs.log'
        super(JobLogHandler, self).__init__(base_filename, mode=mode,
                                            encoding=encoding, delay=1)

    def emit(self, record):
        names_a = record.name.rsplit('.', 1)
        if len(names_a) == 2:
            logname = names_a[1]
        else:
            logname = self.baseFilename

        variables = {'logname': logname,
                     'job_id': getattr(record, 'job_id', "None"),
                     'thread_name': getattr(record, 'threadName', "None")}

        filename = self.filename_format % variables
        if filename in self.file_handles:
            self.stream = self.file_handles[filename]
        else:
            self.baseFilename = filename
            self.stream = self._open()
            self.file_handles[filename] = self.stream
        super(JobLogHandler, self).emit(record)

    def close(self):
        super(JobLogHandler, self).close()
        for fname in self.file_handles:
            f = self.file_handles[fname]
            f.close()
        self.file_handles = {}


# A decorator for abstract classes
def not_implemented_decorator(func):
    def call(self, *args, **kwargs):
        def raise_error(func):
            raise exceptions.AgentNotImplementedException(
                func_name=func.func_name)
        return raise_error(func)
    return call


def generate_password(length=None):
    if length is None:
        length = 8 + random.randint(0, 10)
    selection_set = string.ascii_letters + string.digits + string.punctuation
    pw = ''.join(random.choice(selection_set) for x in range(length))
    return pw


def setup_remote_pydev(host, port):
    try:
        import pydevd

        pydevd.settrace(host,
                        port=port,
                        stdoutToServer=False,
                        stderrToServer=False,
                        suspend=False)
        return True
    except Exception:
        return False


def run_command(conf, cmd_line, cwd=None):
    if type(cmd_line) == list or type(cmd_line) == tuple:
        " ".join([str(i) for i in cmd_line])
    return conf.jr.run_command(cmd_line, cwd=cwd)


def run_script(conf, name, args):
    cmd = conf.get_script_location(name)
    args.insert(0, cmd)
    return run_command(conf, args)


def safe_delete(fname):
    try:
        os.remove(fname)
        return True
    except OSError as osEx:
        if osEx.errno == 2:
            return True
        return False


class Lock(object):

    def __init__(self, conf, timeout, no_fs):
        self._timeout = timeout
        self._no_fs = no_fs
        self._lock_process = None
        self._conf = conf

    def is_locked(self):
        return self._lock_process is not None

    def lock(self):
        pass

    def _lock_service(self):
        (os_fd, lock_file_name) = tempfile.mkstemp(suffix=".lock", prefix="dcm")
        os.close(os_fd)
        (_, _, _, _, _, _, _, _, mtime, _) = os.stat(lock_file_name)

        args = [self._conf.services_directory,
                str(self._timeout),
                lock_file_name]
        (stdout, stderr, rc) = run_script("lockServices")

