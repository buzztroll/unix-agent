"""This module contains a set of helper methods that will assist authors of
dcm-agent extension plugins.
"""
import base64
import json
import logging
import os
import re

import dcm.agent.utils as agent_util
import dcm.agent.logger as dcm_logger

_g_logger = logging.getLogger(__name__)


def base64type_convertor(b64str):
    """a base 64 decoded string"""
    return base64.b64decode(b64str.encode()).decode("utf-8")


def base64type_binary_convertor(b64str):
    """a base 64 decoded byte array"""
    return base64.b64decode(b64str.encode())


def json_param_type(json_str):
    """a string in JSON format"""
    if json_str is None:
        return None
    if type(json_str) == dict:
        return json_str
    if json_str.lower() == "null":
        return None
    return json.loads(json_str)


def user_name(proposed_name):
    """Safe user name"""
    string_name = str(proposed_name)

    # this regex ONLY allows a-z, A-Z, 0-9, _,  -
    # but disallows _ or - at the beginning or end of username
    if re.match("^(?![_-])[a-zA-Z0-9_-]+(?<![_-])$", string_name):
        return proposed_name
    raise ValueError("bad user name")


def secure_delete(conf, file_name):
    """
    Delete a file in a secure manner
    :param conf:  The DCM agent config object.
    :param file_name: The name of the file to delete.
    """
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
    """Run an external executable or script.

    :param conf: The DCM agent config object.
    :param cmd_line: A list that is the command to run and all of its options
    :param cwd: The directory to start in.
    :param in_env: The environment dictionary to use when running the command.
    :param with_sudo: A bool that defines whether to run the command under
                      sudo.
    :return: A 3 tuple (stdout, stderr, return code).
    """
    if with_sudo:
        cmd_line = cmd_line[:]
        cmd_line.insert(0, conf.system_sudo)
        cmd_line.insert(0, '-E')
    return agent_util.run_command(conf, cmd_line, cwd=cwd, in_env=in_env)


def log_to_dcm_console_job_details(job_name=None, details=None):
    """Log a line back to DCM.  Lines logged in this way will show up in the
    DCM console.  This should be used sparingly.

    :param job_name: The name of the command logging this message.
    :param details: The log message string.
    """
    return dcm_logger.log_to_dcm_console_job_details(
        job_name=job_name, details=details)


def safe_delete(fname):
    """Delete a file but do not thrown an error if the files is not there.

    :param fname: The path to the file to delete.
    :return: True if the fine no longer exists.  False if an error occured
             while trying to delete.
    """
    return agent_util.safe_delete(fname)
