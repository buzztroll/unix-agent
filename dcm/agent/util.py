import logging.handlers
import logging

# A logging handler that sets the file location based on the job id and script name
import random
import string
import subprocess
import threading
import exceptions


class JobLogHandler(logging.FileHandler):

    def __init__(self, filename_format="%(logname)s.log", mode='a', encoding=None):
        self.filename_format = filename_format
        self.file_handles = {}
        base_filename = 'jobs.log'
        super(JobLogHandler, self).__init__(base_filename, mode=mode, encoding=encoding, delay=1)

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
            self.stream = self._open();
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


def fork_exe(command_line_args, logger, cwd=None):
    logger.info("Forking the command " + str(command_line_args))
    process = subprocess.Popen(command_line_args,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               cwd=cwd)

    # TODO interate over the output so that it does not all come just at the end
    stdout, stderr = process.communicate()

    logger.info("STDOUT: " + str(stdout))
    logger.info("STDERR: " + str(stderr))
    logger.info("Return code: " + str(process.returncode))

    return process.returncode
