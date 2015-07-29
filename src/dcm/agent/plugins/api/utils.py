import base64
import logging
import os
import re

import dcm.agent.utils as agent_util
import dcm.agent.logger as dcm_logger

_g_logger = logging.getLogger(__name__)


def base64type_convertor(b64str):
    """base 64 decoded string"""
    return base64.b64decode(b64str.encode()).decode("utf-8")


def base64type_binary_convertor(b64str):
    """base 64 decoded string"""
    return base64.b64decode(b64str.encode())


def user_name(proposed_name):
    """Safe user name"""

    string_name = str(proposed_name)

    # this regex ONLY allows a-z, A-Z, 0-9, _,  -
    # but disallows _ or - at the beginning or end of username
    if re.match("^(?![_-])[a-zA-Z0-9_-]+(?<![_-])$", string_name):
        return proposed_name
    raise ValueError("bad user name")


def secure_delete(conf, file_name):
    exe_path = conf.get_script_location("secureDelete")
    (stdout, stderr, rc) = agent_util.run_command(conf, [exe_path, file_name])
    _g_logger.debug("Secure delete executed with %d %s %s" % (rc,
                                                              stdout,
                                                              stderr))
    with open(file_name, "w") as fptr:
        fptr.write("*" * 100)
    if os.path.exists(file_name):
        os.remove(file_name)


def run_command(conf, cmd_line, cwd=None, in_env=None, with_sudo=False):
    if with_sudo:
        cmd_line = cmd_line[:]
        cmd_line.insert(0, conf.system_sudo)
        cmd_line.insert(0, '-E')
    return agent_util.run_command(conf, cmd_line, cwd=cwd, in_env=in_env)


def log_to_dcm_console_job_details(job_name=None, details=None):
    return dcm_logger.log_to_dcm_console_job_details(
        job_name=job_name, details=details)


def safe_delete(fname):
    return agent_util.safe_delete(fname)
