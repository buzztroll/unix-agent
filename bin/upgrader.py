#!/opt/dcm-agent/embedded/agentve/bin/python
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib2


# in this version we only support the upgrade of agents installed with
# unmodifed package defaults
from dcm.agent import config
import time
import psutil


_g_log_file = '/tmp/dcm_agent_upgrade.log'
logging.basicConfig(filename=_g_log_file, level=logging.DEBUG)
_g_logger = logging


def get_installer(url):
    osf, fname = tempfile.mkstemp()
    os.close(osf)
    response = urllib2.urlopen(url)
    html = response.read()
    with open(fname, "w") as fptr:
        fptr.write(html)
    os.chmod(fname, 0755)
    print fname
    return fname


def run_installer(local_exe, pkg_base_url, new_version, backup_dir):

    old_conf = os.path.join(backup_dir, "agent.conf")
    env = os.environ.copy()
    env["AGENT_BASE_URL"] = pkg_base_url
    #env["AGENT_VERSION"] = new_version

    cmd = "sudo -E %s -r %s" % (local_exe, old_conf)
    process = subprocess.Popen(cmd,
                               shell=True,
                               env=env)
    rc = process.wait()
    return rc


def parse_conf():
    conf = config.AgentConfig(["/dcm/etc/agent.conf"])
    return conf


def verify_env():
    needed_files = ["/dcm", "/dcm/etc/agent.conf"]

    for f in needed_files:
        if not os.path.exists(f):
            raise Exception("The file or directory %s must exist in order"
                            " for the upgrade to succeed.")


def backup_conf():
    backup_conf_dir = tempfile.mkdtemp()
    shutil.copy("/dcm/etc/agent.conf", backup_conf_dir)
    # shutil.copy("/dcm/etc/agentdb.sql", backup_conf_dir)
    return backup_conf_dir


def restart_dcm_agent():
    # we must run this as a detached process
    runner_pid = os.getppid()
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            pid = os.fork()
            if pid == 0:
                os.chdir("/")
                os.system("sudo /etc/init.d/dcm-agent stop")
                time.sleep(10)
                _g_logger.info("Getting process information")
                p = psutil.Process(runner_pid)
                _g_logger.info("got process from psutil %s" % p.name)
                kill_list = [i for i in psutil.process_iter()
                             if i.name == p.name and i.pid != os.getpid()]
                _g_logger.warn("Killing this list %s" % str(kill_list))
                for kp in kill_list:
                    try:
                        kp.kill()
                    except Exception as ex:
                        _g_logger.exception("problem killing %d" % kp.pid)

                time.sleep(10)
                _g_logger.info("Starting dcm-agent")
                fin = open(os.devnull, "r")
                fout = open(_g_log_file, "a")
                subprocess.call("sudo /etc/init.d/dcm-agent start",
                                shell=True,
                                stdin=fin, stdout=fout, stderr=fout)
        finally:
            sys.exit(0)


def main(args=sys.argv):
    new_version = args[1]
    old_version = args[2]
    opts_file = args[3]
    url = args[4]
    pkg_base_url = args[5]

    backup_dir = None
    local_exe = None
    verify_env()
    try:
        backup_dir = backup_conf()
        local_exe = get_installer(url)
        rc = run_installer(
            local_exe, pkg_base_url, new_version, backup_dir)
        restart_dcm_agent()
        return rc
    finally:
        if local_exe:
            try:
                os.remove(local_exe)
            except:
                pass
        if backup_dir:
            try:
                shutil.rmtree(backup_dir)
            except:
                pass


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)