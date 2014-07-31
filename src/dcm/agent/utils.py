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
import base64

import os
import tempfile
import datetime
import traceback
import sys
import exceptions
import logging
import random
import string
import re


_g_logger = logging.getLogger(__name__)


class OperationalState(object):
    OK = "OK"
    EXCESS_RESOURCES = "EXCESS_RESOURCES"
    CONSTRAINED_RESOURCES = "CONSTRAINED_RESOURCES"
    TERMINATED = "TERMINATED"
    NOT_RESPONDING = "NOT_RESPONDING"
    AGENT_FAILURE = "AGENT_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"


# A decorator for abstract classes
def not_implemented_decorator(func):
    def call(self, *args, **kwargs):
        def raise_error(func):
            raise exceptions.AgentNotImplementedException(
                func_name=func.func_name)
        return raise_error(func)
    return call


def verify_config_file(opts):
    must_haves = ["connection_type", "cloud_type", "platform_name",
                  "connection_agentmanager_url"]
    warn_haves = ["cloud_metadata_url"]

    for must in must_haves:
        try:
            getattr(opts, must)
        except:
            raise exceptions.AgentOptionValueNotSetException(
                must, msg="Please check your config file.")

    for warn in warn_haves:
        try:
            getattr(opts, warn)
        except:
            _g_logger.warn("Please check the config file.  The value %s is "
                           "missing and could be needed." % warn)


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
                        stdoutToServer=True,
                        stderrToServer=True,
                        suspend=True)

        return True
    except Exception:
        return False


def run_command(conf, cmd_line, cwd=None, env=None):
    log_file = None
    if env is None:
        _, log_file = tempfile.mkstemp(dir=conf.storage_temppath)
        env = {"DCM_USER": conf.system_user,
               "DCM_BASEDIR": conf.storage_base_dir,
               "DCM_SERVICES_DIR": conf.storage_services_dir,
               "DCM_LOG_FILE": log_file}
    rc = conf.jr.run_command(cmd_line, cwd=cwd, env=env)
    if log_file:
        # read everything logged and send it to the logger
        with open(log_file, "r") as fptr:
            for line in fptr.readlines():
                log_to_dcm(logging.INFO, line)
        os.remove(log_file)
    return rc


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
        (os_fd, lock_file_name) = tempfile.mkstemp(suffix=".lock",
                                                   prefix="dcm")
        os.close(os_fd)
        (_, _, _, _, _, _, _, _, mtime, _) = os.stat(lock_file_name)

        args = [self._conf.services_directory,
                str(self._timeout),
                lock_file_name]
        (stdout, stderr, rc) = run_script("lockServices")


def make_friendly_id(prefix, uid):
    str_id = "%s%09d" % (prefix, uid)
    return str_id[0:3] + "-" + str_id[3:6] + "-" + str_id[6:9]


def make_id_string(prefix, uid):
    return "%s%03d" % (prefix, uid)


def get_time_backup_string():
    nw = datetime.datetime.now()
    tm_str = nw.strftime("%Y%m%d.%H%M%S.%f")
    return tm_str


def secure_delete(conf, file_name):
    exe_path = conf.get_script_location("secureDelete")
    (stdout, stderr, rc) = run_command(conf, [exe_path, file_name])
    _g_logger.debug("Secure delete executed with %d %s %s" % (rc,
                                                              stdout,
                                                              stderr))
    with open(file_name, "w") as fptr:
        fptr.write("*" * 100)
    if os.path.exists(file_name):
        os.remove(file_name)


class DeviceTypes(object):
    ROOT = "ROOT"
    EPHEMERAL = "EPHEMERAL"
    SERVICE = "SERVICE"
    CUSTOM = "CUSTOM"


def get_device_mappings(conf):
    command = [conf.get_script_location("listDevices")]

    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)

    device_mapping_list = []
    lines = stdout.split(os.linesep)
    for line in lines:
        parts = line.split()
        if len(parts) != 5:
            continue

        elements = parts[0].split("/")
        device_id = elements[len(elements) - 1]
        file_system = parts[1]
        mount_point = parts[2]
        size = int(parts[3])
        used = int(parts[4])
        if parts[0].startswith("/dev/mapper"):
            encrypted = True
        else:
            encrypted = False

        if mount_point == "/":
            device_type = DeviceTypes.ROOT
        elif mount_point == conf.storage_services_dir:
            device_type = DeviceTypes.SERVICE
        elif mount_point == conf.storage_mountpoint:
            device_type = DeviceTypes.EPHEMERAL
        else:
            device_type = DeviceTypes.CUSTOM

        device_mapping = {
            "device_id": device_id,
            "encrypted": encrypted,
            "file_system": file_system,
            "mount_point": mount_point,
            "size":  size,
            "used": used,
            "device_type": device_type
        }
        device_mapping_list.append(device_mapping)

    return device_mapping_list


def unmount(conf, mount_point):
    command = [conf.get_script_location("unmount"), mount_point]
    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)

    return rc


def mount(conf, device_id, file_system, mount_point):
    if device_id.startswith("es"):
        device_id = "mapper/" + device_id

    command = [conf.get_script_location("mount"),
               device_id, file_system, mount_point]
    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def agent_format(conf, device_id, file_system, mount_point, encryption_key):
    enc_str = str(encryption_key is not None).lower()
    command = [conf.get_script_location("format"),
               device_id,
               file_system,
               mount_point,
               enc_str]
    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def open_encrypted_device(conf, raw_device_id, encrypted_device_id, key_file):
    command = [conf.get_script_location("openEncryption"),
               raw_device_id,
               encrypted_device_id,
               key_file]
    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def close_encrypted_device(conf, encrypted_device_id):
    command = [conf.get_script_location("closeEncryption"),
               encrypted_device_id]
    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def log_to_dcm(lvl, msg, *args, **kwargs):
    l_logger = logging.getLogger("dcm.agent.log.to.agent.manager")
    l_logger.log(lvl, msg, *args, **kwargs)


def build_assertion_exception(logger, msg):
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
    logger.error(msg)


def generate_token():
    l = 30 + random.randint(0, 29)
    token = ''.join(random.choice(string.ascii_letters + string.digits +
                                  "-_!@#^(),.=+") for x in range(l))
    return token


def base64type_convertor(b64str):
    """base 64 decoded string"""
    return base64.b64decode(b64str).decode("utf-8")


def user_name(proposed_name):
    """Safe user name"""

    string_name = str(proposed_name)

    # this regex ONLY allows a-z, A-Z, 0-9, _,  -
    # but disallows _ or - at the beginning or end of username
    if re.match("^(?![_-])[a-zA-Z0-9_-]+(?<![_-])$", string_name):
        return proposed_name
    else:
        return None
