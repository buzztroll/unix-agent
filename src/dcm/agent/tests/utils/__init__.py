import os
import nose.plugins.skip as skip
from dcm.agent import utils


SYSTEM_CHANGING_TEST_ENV = "SYSTEM_CHANGING_TEST"

S3_ACCESS_KEY_ENV = "S3_ACCESS_KEY"
S3_SECRET_KEY_ENV = "S3_SECRET_KEY"


_debugger_connected = False

def connect_to_debugger():
    global _debugger_connected

    PYDEVD_CONTACT = "PYDEVD_CONTACT"
    if PYDEVD_CONTACT in os.environ and not _debugger_connected:
        pydev_contact = os.environ[PYDEVD_CONTACT]
        host, port = pydev_contact.split(":", 1)
        utils.setup_remote_pydev(host, int(port))
        _debugger_connected = True


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
