import os
import traceback
import nose.plugins.skip as skip
import sys
import signal
import time
from dcm.agent import utils


SYSTEM_CHANGING_TEST_ENV = "SYSTEM_CHANGING_TEST"

S3_ACCESS_KEY_ENV = "S3_ACCESS_KEY"
S3_SECRET_KEY_ENV = "S3_SECRET_KEY"


_debugger_connected = False


def _signal_thread_dump(signum, frame):
    msg = build_assertion_exception("SIGNAL DUMP")
    print msg
    with open("/tmp/stack_dump", "w") as fptr:
        fptr.write(msg)


def setup_signal_dumper():
    signal.signal(signal.SIGUSR2, _signal_thread_dump)


def connect_to_debugger():
    global _debugger_connected

    setup_signal_dumper()
    PYDEVD_CONTACT = "PYDEVD_CONTACT"
    if PYDEVD_CONTACT in os.environ and not _debugger_connected:
        pydev_contact = os.environ[PYDEVD_CONTACT]
        host, port = pydev_contact.split(":", 1)
        utils.setup_remote_pydev(host, int(port))
        _debugger_connected = True


def build_assertion_exception(msg):
    details_out = " === Stack trace Begin === " + os.linesep
    for threadId, stack in sys._current_frames().items():
        details_out = details_out + os.linesep + \
            "##### Thread %s #####" % threadId + os.linesep
        for filename, lineno, name, line in traceback.extract_stack(stack):
            details_out = details_out + os.linesep + \
                'File: "%s", line %d, in %s' % (filename, lineno, name)
        if line:
            details_out = details_out + os.linesep + line.strip()

    details_out = details_out + os.linesep + " === Stack trace End === "
    msg = msg + " | " + details_out
    return msg


def test_thread_shutdown():
    # check no threads are running
    n = 0
    while n < 10:
        cnt = len(sys._current_frames().items())
        time.sleep(0.01)
        n += 1
        if cnt < 2:
            return

    if cnt > 1:
        msg = "THE THREAD COUNT IS %d" % cnt
        print msg
        print build_assertion_exception(msg)
        #raise


def get_conf_file(fname="agent.conf"):
    path = os.path.dirname(__file__)
    path = os.path.dirname(path)
    return os.path.join(path, "etc", fname)


def system_changing(func):
    def inner(*args, **kwargs):
        if SYSTEM_CHANGING_TEST_ENV not in os.environ:
            raise skip.SkipTest(
                "Test %s will change your system environment.  "
                "If you are sure you want to do this (ie you are "
                "running in a disposable VM) sent the environment "
                "variable %s" % (func.__name__,
                                 SYSTEM_CHANGING_TEST_ENV))
        return func(*args, **kwargs)
    inner.__name__ = func.__name__
    return inner
