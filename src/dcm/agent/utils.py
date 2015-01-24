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
import subprocess
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


def run_command(conf, cmd_line, cwd=None):
    _, log_file = tempfile.mkstemp(dir=conf.storage_temppath)
    env = {b"DCM_USER": conf.system_user.encode('utf-8'),
           b"DCM_BASEDIR": conf.storage_base_dir.encode('utf-8'),
           b"DCM_TMP_DIR": conf.storage_temppath.encode('utf-8'),
           b"DCM_LOG_FILE": log_file.encode('utf-8'),
           b"DCM_PYTHON": sys.executable.encode('utf-8')}
    if conf.platform_name:
           env[b"DCM_AGENT_PLATFORM_NAME"] = conf.platform_name
    if conf.platform_version:
           env[b"DCM_AGENT_PLATFORM_VERSION"] = conf.platform_version

    if conf.jr is not None:
        rc = conf.jr.run_command(cmd_line, cwd=cwd, env=env)
    else:
        _g_logger.warn("Running without the job runner process")
        process = subprocess.Popen(cmd_line,
                                   shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   cwd=cwd,
                                   env=env)
        stdout, stderr = process.communicate()
        rc = (stdout, stderr, process.returncode)
    if log_file:
        # read everything logged and send it to the logger
        with open(log_file, "r") as fptr:
            for line in fptr.readlines():
                line = line.decode('utf-8')
                if line.strip():
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
    CUSTOM = "CUSTOM"


def get_device_mappings(conf):
    command = [conf.get_script_location("listDevices")]

    (stdout, stderr, rc) = run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)

    try:
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
    except Exception as ex:
        _g_logger.exception(ex.message)
        _g_logger.error("listDevice stdout: " + stdout)
        _g_logger.error("listDevice stderr: " + stderr)
        raise

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


def base64type_binary_convertor(b64str):
    """base 64 decoded string"""
    return base64.b64decode(b64str)


def user_name(proposed_name):
    """Safe user name"""

    string_name = str(proposed_name)

    # this regex ONLY allows a-z, A-Z, 0-9, _,  -
    # but disallows _ or - at the beginning or end of username
    if re.match("^(?![_-])[a-zA-Z0-9_-]+(?<![_-])$", string_name):
        return proposed_name
    raise ValueError("bad user name")


def identify_platform(conf):

    distro_name = None
    distro_version = None

    os_release_path = "/etc/os-release"
    if os.path.exists(os_release_path):
        with open(os_release_path) as fptr:
            for line in fptr.readlines():
                key, value = line.split("=", 1)
                if key == "ID":
                    distro_name = value
                elif key == "VERSION_ID":
                    distro_version = value
        if distro_name and distro_version:
            return distro_name.strip(), distro_version.strip()

    os_release_path = "/etc/lsb-release"
    if os.path.exists(os_release_path):
        with open(os_release_path) as fptr:
            for line in fptr.readlines():
                key, value = line.split("=", 1)
                if key == "DISTRIB_ID":
                    distro_name = value.lower()
                elif key == "DISTRIB_RELEASE":
                    distro_version = value
        if distro_name and distro_version:
            return distro_name.strip(), distro_version.strip()

    lsb = "/usr/bin/lsb_release"
    if os.path.exists(lsb) and os.access(lsb, os.X_OK):
        (stdout, stderr, rc) = run_command(conf, [lsb, "-i"])
        if rc != 0 or not stdout:
            raise exceptions.AgentPlatformNotDetectedException()

        parts = stdout.split()
        if len(parts) != 3:
            raise exceptions.AgentPlatformNotDetectedException()

        cand = parts[2].strip()
        if cand == "Ubuntu":
            distro_name = "ubuntu"
        elif cand == "CentOS":
            distro_name = "centos"
        elif cand == "RedHatEnterpriseServer":
            distro_name = "rhel"
        elif cand == "Debian":
            distro_name = "debian"
        else:
            raise exceptions.AgentPlatformNotDetectedException()

        (stdout, stderr, rc) = run_command(conf, [lsb, "-r"])
        if rc != 0:
            raise exceptions.AgentPlatformNotDetectedException()
        parts = stdout.split()
        distro_version = parts[1].strip()

        return distro_name.strip(), distro_version.strip()

    if os.path.exists("/etc/redhat-release"):
        with open("/etc/redhat-release") as fptr:
            redhat_info = fptr.readline().split()
        if redhat_info[0] == "CentOS":
            distro_version = redhat_info[2]
            distro_name = "centos"
        elif redhat_info[0] == "Red":
            distro_version = redhat_info[3]
            distro_name = "rhel"
        elif redhat_info[0] == "Fedora":
            distro_version = redhat_info[2]
            distro_name = "fedora"
        else:
            raise exceptions.AgentPlatformNotDetectedException()
        return distro_name.strip(), distro_version.strip()

    if os.path.exists("/etc/debian_version"):
        with open("/etc/debian_version") as fptr:
            distro_version = fptr.read().strip()
        distro_name = "debian"
        return distro_name.strip(), distro_version.strip()

    raise exceptions.AgentPlatformNotDetectedException()
