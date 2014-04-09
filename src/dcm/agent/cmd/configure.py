# this program simply creates the configuration file needed by the agent
# it is assumed that all of the directories have already been created with
# the proper permissions

import argparse
import os
import shutil
import subprocess
import sys
import platform
import textwrap
from dcm.agent import config
import ConfigParser

import dcm.agent


# below are the variables with no defaults that must be determined
cloud_choice = None
platform_cloice = None


# below are the variables that have predetermined defaults
default_binaries_path = "/dcm/bin"
default_ephemeral_mountpoint = "/mnt"
default_base_path = "/dcm"
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
                            cloud_choices.values()))
                        # choices=cloud_choices.values())
    parser.add_argument("--url", "-u", dest="url",
                        default=None,
                        help="The location of the dcm web socket listener")

    parser.add_argument("--verbose", "-v", dest="verbose",
                        action='store_true',
                        default=False,
                        help="Increase the amount of output produced by the "
                             "script."),

    parser.add_argument("--initial", "-I", dest="initial",
                        action='store_true',
                        default=False,
                        help=argparse.SUPPRESS),

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

    parser.add_argument("--base-path", "-p",
                        metavar=default_base_path,
                        default=default_base_path,
                        dest="base_path",
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

    parser.add_argument("--user", "-U",
                        dest="user",
                        help="The system user that will run the agent.",
                        default="dcm")

    parser.add_argument("--connection-type", "-C",
                        dest="con_type",
                        help="The type of connection that will be formed "
                             "with the agent manager.",
                        default="ws")
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


def identify_platform(opts):

    if not opts.initial and platform.system().lower() != "linux":
        raise Exception("This agent can only be used on Linux platform.")

    lsb = "/usr/bin/lsb_release"
    if os.path.exists(lsb) and os.access(lsb, os.X_OK):
        rc, stdout, stderr = run_command(" ".join([lsb, "-i"]))
        if rc == 0 and stdout:
            parts = stdout.split()
            if len(parts) == 3:
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

    if opts.initial:
        return None
    raise Exception("The platform could not be determined")


def select_cloud():
    for c in sorted(cloud_choices.keys()):
        col = "%2d) %-13s" % (c, cloud_choices[c])
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


def pick_meta_data(cloud):
    if cloud == "Amazon":
        return "http://169.254.169.254/latest/meta-data/"
    elif cloud == "Eucalyptus":
        return "http://169.254.169.254/1.0/meta-data/"
    elif cloud == "OpenStack":
        return "http://169.254.169.254/openstack/2012-08-10/meta_data.json"
    elif cloud == "CloudStack":
        return "lastest/instance-id"
    elif cloud == "CloudStack3":
        return "latest/local-hostname"
    else:
        return None


def do_py_install(ve_path):
    command = "%s %s" % (os.path.join(
        os.getcwd(), "install-py-mod.sh"), ve_path)
    (rc, stdout, stderr) = run_command(command)
    if rc != 0:
        raise Exception(stderr)


def _default_conf_dict():

    conf_dict = {}
    conf = config.AgentConfig()
    for c in conf.option_list:

        s_d = {}
        if c.section in conf_dict:
            s_d = conf_dict[c.section]
        else:
            conf_dict[c.section] = s_d

        s_d[c.name] = (c.get_help(), c.get_default())
    return conf_dict


def _update_conf_dict(conf_file, conf_dict):

    parser = ConfigParser.SafeConfigParser()
    parser.read([conf_file])

    for s in parser.sections():
        if s in conf_dict:
            sd = conf_dict[s]
        else:
            sd = {}
            conf_dict[s] = sd

        items_list = parser.items(s)
        for (key, value) in items_list:
            help = None
            if key in conf_dict:
                (help, _) = sd[key]
            sd[key] = (help, value)


def write_conf_file(dest_filename, conf_dict):

    with open(dest_filename, "w") as fptr:
        for section_name in conf_dict:
            sd = conf_dict[section_name]
            fptr.write("[%s]%s" % (section_name, os.linesep))

            for item_name in sd:
                (help, value) = sd[item_name]
                if help:
                    help_lines = textwrap.wrap(help, 79)
                    for h in help_lines:
                        fptr.write("# %s%s" % (h, os.linesep))
                if value is None:
                    fptr.write("#%s=" % item_name)
                else:
                    if type(value) == list:
                        value = str(value)[1:-1]
                    fptr.write("%s=%s" % (item_name, str(value)))

                fptr.write(os.linesep)

            fptr.write(os.linesep)


def manage_conf(opts, conf_file_name):

    conf_d = _default_conf_dict()
    _update_conf_dict(conf_file_name, conf_d)

    return conf_d


def merge_opts(conf_d, opts):

    map_opts_to_conf = {
        "cloud": ("cloud", "type"),
        "url": ("connection", "agentmanager_url"),
        "binaries_path": ("storage", "binaries_path"),
        "ephemeral_mountpoint": ("storage", "ephemeral_mountpoint"),
        "base_path": ("storage", "base_dir"),
        "operations_path": ("storage", "operations_path"),
        "services_path": ("storage", "services_dir"),
        "temp_path": ("storage", "temppath"),
        "platform": ("platform", "name"),
    }
    for opts_name in map_opts_to_conf:
        (s, i) = map_opts_to_conf[opts_name]

        if s not in conf_d:
            conf_d[s] = {}
        sd = conf_d[s]
        v = getattr(opts, opts_name, None)
        h = None
        if i in sd:
            (h, _) = sd[i]
        if v is not None:
            sd[i] = (h, v)


def do_plugin(opts):
    dest_plugin_path = os.path.join(opts.base_path, "etc", "plugin.conf")
    dest_logging_path = os.path.join(opts.base_path, "etc", "logging.yaml")

    root_dir = dcm.agent.get_root_location()

    src_pluggin_path = os.path.join(root_dir, "etc", "plugin.conf")
    src_logging_path = os.path.join(root_dir, "etc", "logging.yaml")

    shutil.copy(src_pluggin_path, dest_plugin_path)
    shutil.copy(src_logging_path, dest_logging_path)

    log_file = os.path.join(opts.base_path, "logs", "agent.log")

    os.system("sed -i 's^@LOGFILE_PATH@^%s^' %s" % (log_file,
                                                    dest_logging_path))


def copy_scripts(opts):
    src_script_dir = config.get_python_script_dir()
    dest_dir = os.path.join(opts.base_path, "bin")
    os.system("cp %s %s" % (os.path.join(src_script_dir, 'common-linux', '*'),
                            dest_dir))

    # set common_mod variables
    with open(os.path.join(dest_dir, "variables.sh"), "w") as fptr:
        fptr.write("DCM_USER=%s" % opts.user)
        fptr.write(os.linesep)
        fptr.write("DCM_BASEDIR=%s" % opts.base_path)
        fptr.write(os.linesep)


def set_values(conf_d, opts):
    #  This function sets the cinfiguration forced values
    forced_values = {
        "logging": {"configfile":
                    os.path.join(opts.base_path, "etc", "logging.yaml")},
        "connection": {"type": "ws"},
        "storage": {"script_dir": os.path.join(opts.base_path, "bin")}
    }

    for section in forced_values:
        for item in forced_values[section]:
            (h, _) = conf_d[section][item]
            forced = forced_values[section][item]
            conf_d[section][item] = (h, forced)


def get_url():
    default = "wss://provisioning.enstratius.com:16309/ws"
    print "Please enter the contact string of the agent manager (%s)" % default
    url = sys.stdin.readline().strip()
    if not url:
        return default

    # validate
    la = url.split(":")
    if len(la) != 2:
        raise Exception("The format of the agent manager url is no valid. "
                        "It must include a port.  %s" % url)
    return url


def enable_start_agent(opts):
    print "Would you like to start the agent on boot? (Y/n)"
    ans = sys.stdin.readline().strip()
    if ans == "" or ans.lower() == "y" or ans.lower == "yes":
        if os.path.exists("/usr/sbin/update-rc.d"):
            os.system("update-rc.d dcm-agent defaults")
            os.system("/etc/init.d/dcm-agent start")
        # TODO other platforms


def main():
    parser = setup_command_line_parser()
    opts = parser.parse_args(args=sys.argv[1:])

    try:
        if opts.cloud is not None and opts.cloud not in cloud_choices.values():
            raise Exception("%s is not a valid cloud choice.  It must be one "
                            "of %s" % (opts.cloud,
                                       str(cloud_choices.values())))
        if opts.platform is None:
            opts.platform = identify_platform(opts)
        if opts.cloud is None and not opts.initial:
            opts.cloud = select_cloud()
        if opts.url is None and not opts.initial:
            opts.url = get_url()

        do_plugin(opts)

        conf_file_name = os.path.join(opts.base_path, "etc", "agent.conf")
        conf_d = manage_conf(opts, conf_file_name)
        merge_opts(conf_d, opts)
        set_values(conf_d, opts)
        write_conf_file(conf_file_name, conf_d)
        copy_scripts(opts)

        if not opts.initial:
            enable_start_agent(opts)

    except Exception as ex:
        print >> sys.stderr, ex.message
        if opts.verbose:
            raise


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
