import argparse
import os
import subprocess
import sys
import platform

import virtualenv


# below are the variables with no defaults that must be determined
dcm_url = "https://enstratius.com:8080"
cloud_choice = None
platform_cloice = None


# below are the variables that have predetermined defaults
default_binaries_path = "/enstratus/bin"
default_ephemeral_mountpoint = "/mnt"
default_enstratus_path = "/enstratus"
default_operations_path = "/mnt"
default_services_path = "/mnt/services"
default_temp_path = "/mnt/tmp"


platform_choices = ["ubuntu", "el", "debian", "suse"]


cloud_choices = {
    1: "Amazon",
    2: "Atmos",
    3: "ATT",
    4: "Azure",
    5: "Bluelock",
    6: "CloudCentral",
    7: "CloudSigma",
    8: "CloudStack",
    9: "CloudStack3",
    10: "Eucalyptus",
    11: "GoGrid",
    12: "Google",
    13: "IBM",
    14: "Joyent",
    15: "OpenStack",
    16: "Rackspace",
    17: "ServerExpress",
    18: "Terremark",
    19: "VMware",
    20: "Other",
}

def setup_command_line_parser():
    parser = argparse.ArgumentParser(
        description='DCM Agent Installer for linux.')

    parser.add_argument("--cloud", "-c", metavar="{Amazon, etc...}",
                        dest="cloud",
                        help="The cloud where this virtual machine will be "
                             "run.  Options: %s" % ", ".join(
                            cloud_choices.values()),
                        choices=cloud_choices.values())
    parser.add_argument("--url", "-u", dest="url",
                        default=dcm_url,
                        help="The location of the dcm web socket listener")

    parser.add_argument("--verbose", "-v", dest="verbose",
                        action='store_true',
                        default=False,
                        help="Increase the amount of output produced by the "
                             "script."),

    parser.add_argument("--binaries-path", "-b",
                        metavar=default_binaries_path,
                        default=default_binaries_path,
                        dest="binaries_path",
                        help="The location of binary files relevant to the "
                             "agent.")

    parser.add_argument("--ephemeral-mountpoint", "-e",
                        metavar=default_ephemeral_mountpoint,
                        default=default_ephemeral_mountpoint,
                        dest="ephemeral_mountpoint",
                        help="The location of ephemeral mount point.")

    parser.add_argument("--enstratus-path", "-p",
                        metavar=default_enstratus_path,
                        default=default_enstratus_path,
                        dest="enstratus_path",
                        help="The path to enstratius")

    parser.add_argument("--operations-path", "-o",
                        metavar=default_operations_path,
                        default=default_operations_path,
                        dest="operations_path",
                        help="The operations path")

    parser.add_argument("--services-path", "-s",
                        metavar=default_services_path,
                        default=default_services_path,
                        dest="services_path",
                        help="The services path")

    parser.add_argument("--temp-path", "-t",
                        metavar=default_temp_path,
                        default=default_temp_path,
                        dest="temp_path",
                        help="The temp path")

    parser.add_argument("--platform", "-P",
                        dest="platform",
                        help="The platform where this is being installed. "
                             "It is recommended that you only set this option "
                             "if this script fails to determine it for you.",
                        choices=platform_choices)
    return parser


def run_command(cmd):
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            env={})
        stdout, stderr = process.communicate()
        rc = process.returncode
    except Exception as ex:
        rc = 1
        stdout = None
        stderr = ex.message
    return (rc, stdout, stderr)


def identify_platform():

    if platform.system().lower() != "linux":
        raise Exception("This agent can only be used on Linux platform.")

    lsb = "/usr/bin/lsb_release"
    if os.path.exists(lsb) and os.access(lsb, os.X_OK):
        rc, stdout, stderr = run_command(" ".join([lsb, "-i"]))
        if rc == 0 and stdout:
            parts = stdout.split()
            if parts == 3:
                cand = parts[2].strip()
                if cand == "Ubuntu":
                    return "ubuntu"
                elif cand == "CentOS":
                    return "el"
                elif cand == "RedHatEnterpriseServer":
                    return "el"
                elif cand == "SUSE LINUX":
                    return "suse"
                elif cand == "n/a":
                    return "el"

    if os.path.exists("/etc/redhat-release"):
        with open("/etc/redhat-release") as fptr:
            redhat_info = fptr.readline().split()[0]
            if redhat_info == "CentOS":
                return "el"
            elif redhat_info == "Red":
                return "el"
    if os.path.exists("/etc/debian_version"):
        return "debian"
    if os.path.exists("/etc/SuSE-release"):
        return "suse"
    if os.path.exists("/etc/system-release"):
        with open("/etc/system-release") as fptr:
            line = fptr.readline().strip().lower()
            if line.find("amazon linux ami") >= 0:
                return "el"

    raise Exception("The platform could not be determined")


def select_cloud():

    for c in sorted(cloud_choices.keys()):
        col = "%2d) %-13s" %(c, cloud_choices[c])
        print col

    cloud = None
    while cloud is None:
        input = raw_input("Select your cloud: ")
        try:
            ndx = int(input)
            cloud = cloud_choices[ndx]
        except:
            print "%s is not a valid choice." % input
    return cloud


def do_virtual_env(opts, ve_path):
    orig_args = sys.argv
    sys.argv = ["virtualenv.py", "--no-site-packages", ve_path]
    try:
        virtualenv.main()
    finally:
        sys.argv = orig_args


def make_directories(opts):
    dirs = [
            opts.binaries_path,
            opts.ephemeral_mountpoint,
            opts.enstratus_path,
            opts.operations_path,
            opts.services_path,
            opts.temp_path,
            os.path.join(opts.enstratus_path, "etc"),
            os.path.join(opts.enstratus_path, "bin"),
            ]

    for d in dirs:
        try:
            os.makedirs(d)
        except OSError as osEx:
            if osEx.errno != 17:
                raise Exception("The directory %s could not be made: %s " %
                                (d, osEx.message))


def do_py_install(ve_path):
    command = "%s %s" % (os.path.join(
        os.getcwd(), "install-py-mod.sh"), ve_path)
    (rc, stdout, stderr) = run_command(command)
    if rc != 0:
        raise Exception(stderr)


def _sed(sub_list, source, dest):
    with open(dest, "w") as dest_fptr:
        with open(source, "r") as source_ptr:
            for line in source_ptr.readlines():
                for o, s in sub_list:
                    line = line.replace(o, s)
                dest_fptr.write(line)


def do_conf_files(opts):

    source_dir = os.path.join(os.path.dirname(os.getcwd()), "etc")
    dest_dir = os.path.join(opts.enstratus_path, "etc")

    log_sub = [("@LOGFILE_PATH@",
                os.path.join(opts.enstratus_path, "agent.log"))]
    _sed(log_sub,
         os.path.join(source_dir, "logging.yaml.template"),
         os.path.join(dest_dir, "logging.yaml"))

    _sed([],
         os.path.join(source_dir, "plugin.conf.template"),
         os.path.join(dest_dir, "plugin.conf"))

    agent_sub = [
        ("@TEMP_PATH@", opts.temp_path),
        ("@SERVICE_DIR@", opts.services_path),
        ("@CLOUD_TYPE@", opts.cloud),
        ("@AGENT_MANAGER_URL@", opts.url + "/ws")
    ]
    _sed(agent_sub,
         os.path.join(source_dir, "agent.conf.template"),
         os.path.join(dest_dir, "agent.conf"))

    return dest_dir


def write_exe(opts, ve):
    agent_exe_fname = os.path.join(opts.enstratus_path, "bin", "agent.sh")

    agent_script = """
#!/bin/bash

. %(install_dir)s/bin/activate
%(ve_dir)s/bin/dcm-agent -c %(install_dir)s/etc/agent.conf
""" % {"install_dir": opts.enstratus_path, "ve_dir": ve}
    with open(agent_exe_fname, "w") as f:
        f.write(agent_script)



def main():

    parser = setup_command_line_parser()
    opts = parser.parse_args(args=sys.argv[1:])

    ve_path = os.path.join(opts.enstratus_path, "VE")

    try:
        if opts.platform is None:
            opts.platform = identify_platform()
        if opts.cloud is None:
            opts.cloud = select_cloud()
        make_directories(opts)
        do_virtual_env(opts, ve_path)

        do_py_install(ve_path)

        dest_dir = do_conf_files(opts)

        write_exe(opts, ve_path)

        print "The agent installation was successful."
        print "Further customizations can be made in the configuration files " \
              "found in the directory %s" % dest_dir

    except Exception as ex:
        print >> sys.stderr, ex.message
        if opts.verbose:
            raise


if __name__ == "__main__":
    main()
