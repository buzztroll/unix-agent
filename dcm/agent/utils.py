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


def run_command(conf, args):
    _g_logger.info("Forking the command " + str(args))
    args = ' '.join(args)  # for some reason i cannot just pass the array.
                           # at least should do a shell join
    script_dir = conf.get_script_dir()
    process = subprocess.Popen(args,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               cwd=script_dir)
    stdout, stderr = process.communicate()

    _g_logger.info("command %s:  STDOUT: %s" + str(stdout))
    _g_logger.info("STDERR: " + str(stderr))
    _g_logger.info("Return code: " + str(process.returncode))
    return (stdout, stderr, process.returncode)

def run_script(conf, name, args):
    cmd = conf.get_script_location(name)
    args = [cmd].extend(args)
    return run_command(conf, args)

