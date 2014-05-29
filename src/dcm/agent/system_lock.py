import logging
import os
import subprocess
import datetime
import threading
import time
import dcm.agent.exceptions as exceptions


_g_logger = logging.getLogger(__name__)


class ServiceLockProcess(object):

    def __init__(self, name, exe_path, temp_file_path, service_path, timeout):
        self.name = name
        with open(temp_file_path, "w") as fptr:
            fptr.write("A lock file")
        self._locked = False
        self._exe_path = exe_path
        self._lock_file = temp_file_path
        (_, _, _, _, _, _, _, _, self._start_time, _) =\
            os.stat(self._lock_file)

        cmd = [exe_path, service_path, self._lock_file, str(timeout), name]
        _g_logger.debug("Running lock command %s" % str(cmd))
        self._process = subprocess.Popen(" ".join(cmd),
                                         shell=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         stdin=subprocess.PIPE)

    def is_locked(self):
        # wait for the tmp file to be touched
        x = self._process.poll()
        if x is not None:
            # this means the process finished, we do not want this to happen
            # until we have told it to unlock
            _g_logger.warn("The lock process %s ended before it was unlocked: "
                           "%s :: %s" % (self._exe_path,
                                         self._process.stdout,
                                         self._process.stderr))
            raise exceptions.AgentPluginOperationException(
                "The lock exe ended before it should have")
        (_, _, _, _, _, _, _, _, mtime, _) = os.stat(self._lock_file)
        _g_logger.warn("TIMES ARE %s || %s" % (self._start_time, mtime))
        return self._start_time < mtime

    def unlock(self):
        try:
            _g_logger.debug("UNLOCK %s" % self.name)
            (o, e) = self._process._communicate(input="UNLOCK"+os.linesep)
            self._locked = False
            _g_logger.debug("UNLOCK OUTPUT %s | %s" % (o, e))
        except Exception as ex:
            # mark as unknown
            _g_logger.exception("Failed to unlock: %s" % str(ex))


class ServiceLock(object):

    def __init__(self, conf):
        self._cond = threading.Condition()
        self._locked = False
        self._conf = conf
        self._lock_processes = []

    def _get_service_list(self):
        services_to_lock = []
        for f in os.listdir(self._conf.storage_services_dir):
            if f[0] == "a":
                lock_cmd = os.path.join(self._conf.storage_services_dir,
                                        f,
                                        "bin",
                                        "enstratus-lock")
                if os.path.exists(lock_cmd):
                    _g_logger.debug("Found service to debug %s" % f[1:])
                    services_to_lock.append((f, lock_cmd))
        return services_to_lock

    def is_locked(self):
        return self._locked

    def lock(self, timeout):
        if self.is_locked():
            raise exceptions.AgentPluginOperationException("Already locked")

        lock_timeout = datetime.datetime.now() + \
            datetime.timedelta(milliseconds=timeout)

        self._cond.acquire()
        try:
            self._locked = True
            service_list = self._get_service_list()
            temp_file_path = self._conf.get_temp_file("enstratus.lock")

            ndx = 0
            for name, service_path in service_list:
                service_temp_file_path = temp_file_path + "." + str(ndx)
                try:
                    service_lock = ServiceLockProcess(
                        name, service_path, service_temp_file_path,
                        self._conf.storage_services_dir, timeout)
                    self._lock_processes.append(service_lock)
                except Exception as ex:
                    _g_logger.exception("Failed to start lock process %s.  We"
                                        "just continue on." % service_path)
                ndx += 1

            # all have been started, now wait for all to be locked
            locked = False
            while not locked:
                now = datetime.datetime.now()
                if now > lock_timeout:
                    raise exceptions.AgentPluginOperationException(
                        "Lock timeout")
                locked = True
                for s in self._lock_processes:
                    if not s.is_locked():
                        locked = False
                if not locked:
                    # we do not want to allow for an unlock before the lock is
                    # complete
                    _g_logger.debug("Sleeping waiting for the lock")
                    time.sleep(0.5)
        except Exception as ex:
            # unlock any service that was locked
            _g_logger.exception("An exception occurred while trying to lock "
                                "services: %s" % str(ex))
            self._unlock()
            raise ex
        finally:
            self._cond.release()

    def _unlock(self):
        _g_logger.debug("Walking the processes to unlock %s"
                        % str(self._lock_processes))
        for s in self._lock_processes:
            s.unlock()
        self._lock_processes = []

    def unlock(self):
        _g_logger.debug("Unlocking the services")
        self._cond.acquire()
        try:
            self._locked = False
            self._unlock()
        finally:
            self._cond.release()


# this object is assumed to be running in a nonthreaded python env, thus
# we can just fork out programs
class FileSystemLock(object):

    def __init__(self, conf):
        self._conf = conf

    def _exec(self, cmd, name):
        p = subprocess.Popen(cmd,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        (stdoutdata, stderrdata) = p.communicate()
        msg = "%s ran with output %s | %s" % (name, stdoutdata, stderrdata)
        _g_logger.debug(msg)
        if p.returncode != 0:
            raise exceptions.AgentPluginOperationException(msg)

    def lock(self):
        exe_path = self._conf.get_script_location("lockFileSystems")
        self._exec(exe_path, "lockFileSystems")

    def unlock(self):
        exe_path = self._conf.get_script_location("unlockFileSystems")
        self._exec(exe_path, "unlockFileSystems")


class ChildProcessLockMgr(object):
    def __init__(self, conf):
        self._service_lock = None
        self._fs_lock = None
        self._conf = conf

    def lock(self, timeout, lock_filesystem):
        self._service_lock = ServiceLock(self._conf)
        self._service_lock.lock(timeout)
        if lock_filesystem:
            self._fs_lock = FileSystemLock(self._conf)
            self._fs_lock.lock()

    def unlock(self):
        _g_logger.debug("The child manager received an unlock request")
        if not self._service_lock:
            raise exceptions.AgentPluginOperationException(
                "The agent is not locked")
        if self._fs_lock:
            self._fs_lock.unlock()
        self._service_lock.unlock()
