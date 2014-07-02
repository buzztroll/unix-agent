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
import urlparse
from dcm.agent import config
import ConfigParser

import dcm.agent


# below are the variables with no defaults that must be determined
cloud_choice = None
platform_cloice = None


platform_choices = ["ubuntu", "el", "debian", "suse"]
g_user_env_str = "DCM_USER"
g_basedir_env_str = "DCM_BASEDIR"

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

    parser.add_argument("--interactive", "-i", dest="interactive",
                        action='store_true',
                        default=False,
                        help="Run an interactive session where questions "
                             "will be asked and answered vi stdio."),

    parser.add_argument("--base-path", "-p",
                        dest="base_path",
                        help="The path to enstratius")

    parser.add_argument("--mount-point", "-m",
                        dest="mount_path",
                        help="The path to mount point")

    parser.add_argument("--on-boot", "-B",
                        dest="on_boot",
                        action='store_true',
                        default=False,
                        help="Setup the agent to start when the VM boots")

    parser.add_argument("--services-path", "-s",
                        dest="services_path",
                        help="The services path")

    parser.add_argument("--reload-conf", "-r",
                        dest="reload",
                        help="The previous config file that will be used "
                             "to populate defaults.")

    parser.add_argument("--temp-path", "-t",
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
                        help="The system user that will run the agent.")

    parser.add_argument("--connection-type", "-C",
                        dest="con_type",
                        help="The type of connection that will be formed "
                             "with the agent manager.")

    parser.add_argument("--logfile", "-l",
                        dest="logfile")
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


def _get_input(prompt):
    return raw_input(prompt)


def select_cloud(default="Amazon"):
    for c in sorted(cloud_choices.keys()):
        col = "%2d) %-13s" % (c, cloud_choices[c])
        print col

    cloud = None
    while cloud is None:
        input = _get_input("Select your cloud (%s): " % default)
        input = input.strip()
        if not input:
            input = default
        if input in [i.lower() for i in cloud_choices.values()]:
            return input
        try:
            ndx = int(input)
            cloud = cloud_choices[ndx]
        except:
            print "%s is not a valid choice." % input
    return cloud


def pick_meta_data(conf_d):
    (_, cloud) = conf_d["cloud"]["type"]
    if cloud == "Amazon":
        mu = "http://169.254.169.254/latest/meta-data/"
    elif cloud == "Eucalyptus":
        mu = "http://169.254.169.254/1.0/meta-data/"
    elif cloud == "OpenStack":
        mu = "http://169.254.169.254/openstack/2012-08-10/meta_data.json"
    elif cloud == "Google":
        mu = "http://metadata.google.internal/computeMetadata/v1"
    elif cloud == "CloudStack":
        mu = "lastest/instance-id"
    elif cloud == "CloudStack3":
        mu = "latest/local-hostname"
    else:
        return None

    (h, _) = conf_d["cloud"]["metadata_url"]
    conf_d["cloud"]["metadata_url"] = (h, mu)


def get_default_conf_dict():
    conf_dict = {}
    option_list = config._build_options_list()

    for c in option_list:

        s_d = {}
        if c.section in conf_dict:
            s_d = conf_dict[c.section]
        else:
            conf_dict[c.section] = s_d

        s_d[c.name] = (c.get_help(), c.get_default())
    return conf_dict


def update_from_config_file(conf_file, conf_dict):
    # pull from the existing config file
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


def make_dirs(conf_d):
    print "Making the needed directories..."

    (_, base_path) = conf_d["storage"]["base_dir"]

    dirs_to_make = [
        (base_path, 0755),
        (os.path.join(base_path, "bin"), 0750),
        (conf_d["storage"]["script_dir"][1], 0750),
        (os.path.join(base_path, "custom"), 0755),
        (os.path.join(base_path, "custom", "bin"), 0755),
        (os.path.join(base_path, "etc"), 0755),
        (os.path.join(base_path, "logs"), 0755),
        (os.path.join(base_path, "home"), 0750),
        (os.path.join(base_path, "cfg"), 0750),
        (conf_d["storage"]["services_dir"][1], 0755),
        (conf_d["storage"]["mountpoint"][1], 0750),
        (os.path.join(conf_d["storage"]["mountpoint"][1], "tmp"), 0750),
        (conf_d["storage"]["temppath"][1], 01777),
    ]

    for (dir, mod) in dirs_to_make:
        try:
            print "    %s" % dir
            os.mkdir(dir)
        except OSError as ex:
            if ex.errno != 17:
                raise
        os.chmod(dir, mod)

    print "...Done."


def do_set_owner_and_perms(conf_d):
    (_, script_dir) = conf_d["storage"]["script_dir"]
    (_, base_path) = conf_d["storage"]["base_dir"]
    (_, services_path) = conf_d["storage"]["services_dir"]
    (_, user) = conf_d["system"]["user"]

    for f in os.listdir(script_dir):
        os.chmod(os.path.join(script_dir, f), 0550)
    cfg_dir = os.path.join(base_path, "cfg")
    for f in os.listdir(cfg_dir):
        os.chmod(os.path.join(cfg_dir, f), 0640)

    with open(os.path.join(script_dir, "variables.sh"), "w") as fptr:
        fptr.write("DCM_USER=%s" % user)
        fptr.write(os.linesep)
        fptr.write("DCM_BASEDIR=%s" % base_path)
        fptr.write(os.linesep)
        fptr.write("DCM_SERVICES_DIR=%s" % services_path)
        fptr.write(os.linesep)

    print "Changing ownership to %s:%s" % (user, user)
    os.system("chown -R %s:%s %s" % (user, user, base_path))
    os.system("chown -R %s:%s /mnt/tmp" % (user, user))
    os.system("chown -R root:root /tmp")


def merge_opts(conf_d, opts):

    map_opts_to_conf = {
        "cloud": ("cloud", "type"),
        "user": ("system", "user"),
        "url": ("connection", "agentmanager_url"),
        "base_path": ("storage", "base_dir"),
        "services_path": ("storage", "services_dir"),
        "temp_path": ("storage", "temppath"),
        "platform": ("platform", "name"),
        "con_type": ("connection", "type"),
        "mount_path": ("storage", "mountpoint")
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


def do_plugin_and_logging_conf(conf_d, opts):
    (_, base_dir) = conf_d["storage"]["base_dir"]
    (_, dest_plugin_path) = conf_d["plugin"]["configfile"]
    (_, dest_logging_path) = conf_d["logging"]["configfile"]

    root_dir = dcm.agent.get_root_location()

    src_pluggin_path = os.path.join(root_dir, "etc", "plugin.conf")
    src_logging_path = os.path.join(root_dir, "etc", "logging.yaml")

    shutil.copy(src_pluggin_path, dest_plugin_path)
    shutil.copy(src_logging_path, dest_logging_path)

    if opts.logfile is None:
        log_file = os.path.join(base_dir, "logs", "agent.log")
    else:
        log_file = opts.logfile

    with open(src_logging_path, "r") as fptr:
        lines = fptr.readlines()

    with open(dest_logging_path, "w") as fptr:
        for line in lines:
            line = line.replace("@LOGFILE_PATH@", log_file)
            fptr.write(line)


def copy_scripts(conf_d):
    (h, dest_dir) = conf_d["storage"]["script_dir"]
    src_script_dir = config.get_python_script_dir()
    os.system("cp %s %s" % (os.path.join(src_script_dir, 'common-linux', '*'),
                            dest_dir))


def update_relative_paths(conf_d):
    (_, base_dir) = conf_d["storage"]["base_dir"]

    def _val_update(section_name, item_name, default_val):
        h = ""
        try:
            (h, val) = conf_d[section_name][item_name]
        except:
            val = None
        if val is None:
            val = os.path.join(base_dir, default_val)
            conf_d[section_name][item_name] = (h, val)

    _val_update("logging", "configfile", "etc/logging.yaml")
    _val_update("plugin", "configfile", "etc/plugin.conf")
    _val_update("storage", "script_dir", "bin")


def get_url(default=None):
    if not default:
        default = "wss://provisioning.enstratius.com:16309/ws"
    print "Please enter the contact string of the agent manager (%s)" % default
    url = sys.stdin.readline().strip()
    if not url:
        return default

    # validate
    try:
        up = urlparse.urlparse(url)
        int(up.port)
    except Exception as ex:
        raise Exception("The agent manager contact %s is not a valid url"
                        % url)
    allowed_schemes = ["ws", "wss"]
    if up.scheme not in allowed_schemes:
        raise Exception("The url %s does not consist of an allowed scheme. "
                        "Only the follow schemes are allows %s"
                        % (url, str(allowed_schemes)))
    return url


def enable_start_agent(opts):
    ask = opts.interactive
    on_boot = opts.on_boot
    if on_boot:
        ask = False

    if ask:
        print "Would you like to start the agent on boot? (Y/n)"
        ans = sys.stdin.readline().strip()
        on_boot = ans == "" or ans.lower() == "y" or ans.lower() == "yes"
    if on_boot:
        if os.path.exists("/usr/sbin/update-rc.d"):
            os.system("update-rc.d dcm-agent defaults")
        # TODO other platforms


def do_interactive(opts, conf_d):
    if not opts.interactive:
        return
    (h, cloud_type) = conf_d["cloud"]["type"]
    cloud_type = select_cloud(default=cloud_type)
    conf_d["cloud"]["type"] = (h, cloud_type)
    (h, url) = conf_d["connection"]["agentmanager_url"]
    url = get_url(default=url)
    conf_d["connection"]["agentmanager_url"] = (h, url)


def gather_values(opts):
    # get the default values based on the defaults set in the config object
    conf_d = get_default_conf_dict()
    # if we are reloading from a file overide the defaults with what is in
    # that file
    if opts.reload:
        update_from_config_file(opts.reload, conf_d)
    # override any values passed in via options
    merge_opts(conf_d, opts)
    # set defaults for relative paths
    update_relative_paths(conf_d)
    (h, plat) = conf_d["platform"]["name"]
    if not plat:
        plat = identify_platform(opts)
        conf_d["platform"]["name"] = (h, plat)

    return conf_d


def main(argv=sys.argv[1:]):
    parser = setup_command_line_parser()
    opts = parser.parse_args(args=argv)

    conf_d = gather_values(opts)
    do_interactive(opts, conf_d)
    pick_meta_data(conf_d)

    # before writing anything make sure that all the needed values are
    # set
    if not opts.initial:
        if not conf_d["system"]["user"]:
            raise Exception("You must set the user name that will run "
                            "this service.")
        if not conf_d["storage"]["base_dir"]:
            raise Exception("You must set the base dir for this service "
                            "installation.")

    try:
        make_dirs(conf_d)
        copy_scripts(conf_d)
        do_plugin_and_logging_conf(conf_d, opts)
        (_, base_dir) = conf_d["storage"]["base_dir"]
        conf_file_name = os.path.join(base_dir, "etc", "agent.conf")
        write_conf_file(conf_file_name, conf_d)
        do_set_owner_and_perms(conf_d)
        if not opts.initial:
            enable_start_agent(opts)

    except Exception as ex:
        print >> sys.stderr, ex.message
        if opts.verbose:
            raise
    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
