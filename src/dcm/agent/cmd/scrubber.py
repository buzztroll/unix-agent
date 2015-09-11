import argparse
import os
import pwd
import re
import sys
import tarfile


opts_msg = """DCM Agent Image Preparation.

*** THIS PROGRAM WILL DELETE SYSTEM FILES! ***

This program prepares the virtual instance on which it is running for the
creation of a safe image.  Depending in the options given it will delete
logs, private keys, and other files that could contain secrets or other
information that could be damaging when running a child instance.

To backup all of the information that it will remove please use the
--rescue-tar option.  This will first put the file in a tarball before removing
it.  This file can then be untarred to restore the removed files.  However,
this file should be manually copied off the server and then safely removed
before the image creation occurs.
"""

_g_tarfile_output_message = """
******************************************************************************
The file %s contains secrets!
This file is useful for restoring any information that this program deleted,
however before creating an image from this running VM you must copy it off of
the server and then securely delete it!
******************************************************************************
"""


def setup_command_line_parser():
    parser = argparse.ArgumentParser(description=opts_msg)
    parser.add_argument("-v", "--verbose",
                        help="Increase the amount of output.",
                        action='count', default=1)
    parser.add_argument("-r", "--rescue-tar",
                        help="Create a tarball that can be used to recover the secrets that this will erase.",
                        default=None)
    parser.add_argument("-c", "--cloud-init",
                        help="Delete cloud-init cache and logs.",
                        action="store_true")
    parser.add_argument("-d", "--dhcp", help="Delete cached dhcp leases.",
                        action="store_true")
    parser.add_argument("-H", "--history", help="Delete history files.",
                        action="store_true")
    parser.add_argument("-k", "--private-keys",
                        help="Delete private key files.",
                        action="store_true")
    parser.add_argument("-a", "--authorized-keys",
                        help="Delete authorized key files.",
                        action="store_true")
    parser.add_argument("-A", "--agent",
                        help="Delete dcm agent files.",
                        action="store_true")
    parser.add_argument("-X", "--agent_running",
                        help=argparse.SUPPRESS,
                        action="store_true")
    parser.add_argument("-l", "--clean-logs", help="Delete system log files.",
                        action="store_true")
    parser.add_argument("-b", "--batch",
                        help="Run the program without interrupting the user.  This could cause their to be no rescue file.",
                        action="store_true")
    return parser


def console_output(opts, level, *args):
    if level > opts.verbose:
        return
    print(*args)


def get_secure_delete():
    possible_locations = ['/usr/bin/srm',
                          '/usr/sbin/srm',
                          '/usr/local/bin/srm']

    srm_path = None
    for p in possible_locations:
        if os.path.exists(p):
            srm_path = p
            break

    def srm_remove(opts, tar, path):
        if tar is not None:
            tar.add(path)

        console_output(opts, 2, "Securely deleting %s" % path)
        rc = os.system("%s  -f -z %s" % (srm_path, path))
        if rc != 0:
            raise Exception("Failed to remove %s" % path)

    def python_rm(opts, tar, path):
        if tar is not None:
            tar.add(path)
        console_output(opts, 2, "Deleting %s" % path)
        os.remove(path)

    if srm_path:
        return srm_remove
    return python_rm


secure_delete = get_secure_delete()


def delete_history(opts, tar):
    console_output(opts, 1, "Deleting all users history files...")

    lookfor = '.*hist*'
    all_users = pwd.getpwall()
    user_homes = [user_home[5] for user_home in all_users]
    for base_dir in user_homes:
        for (dirpath, dirname, filename) in os.walk(base_dir):
            for file in filename:
                if re.match(lookfor, file):
                    secure_delete(opts, tar, file)


def is_privatekey(keyfile):
    with open(keyfile, 'r') as f:
        if f.readline() == '-----BEGIN RSA PRIVATE KEY-----\n':
            return True
    return False


def delete_private_keys(opts, tar):
    console_output(opts, 1, "Deleting all users private key files...")

    all_users = pwd.getpwall()
    user_homes = [user_home[5] for user_home in all_users]
    for base_dir in user_homes:
        ssh_dir = os.path.join(base_dir, '.ssh')
        for (dirpath, dirname, filenames) in os.walk(ssh_dir):
            for file in filenames:
                filepath = os.path.join(dirpath, file)
                if is_privatekey(filepath):
                    secure_delete(opts, tar, filepath)


def delete_authorize_keys(opts, tar, base_dir):
    console_output(opts, 1, "Deleting all users authorized key files...")

    ssh_authorized_keys = os.path.join(base_dir, '.ssh/authorized_keys')
    if os.path.exists(ssh_authorized_keys):
        secure_delete(opts, tar, ssh_authorized_keys)


def delete_cloud_init_cache(opts, tar):
    console_output(opts, 1, "Deleting cloud-init data files...")

    cloud_init_data_path = "/var/lib/cloud/data/"
    for (dirpath, dirname, filenames) in os.walk(cloud_init_data_path):
            for file in filenames:
                filepath = os.path.join(dirpath, file)
                if is_privatekey(filepath):
                    secure_delete(opts, tar, filepath)


def clean_logs(opts, tar):
    lookfor_strs = ['.*.log', '.*.gz']

    dir_list = ['/var/log',]
    for base_dir in dir_list:
        for (dirpath, dirname, filename) in os.walk(base_dir):
            for file in filename:
                found = False
                for lookfor in lookfor_strs:
                    if re.match(lookfor, file):
                        found = True
                        break
                if found:
                    secure_delete(opts, tar, file)


def clean_agent_files(opts, tar):
    console_output(opts, 2, "Cleaning the agent files.")
    files_to_clean = ['/dcm/secure/token',
                      '/var/lib/waagent/provisioned',
                      '/tmp/boot.log',
                      '/tmp/agent_info.tar.gz',
                      '/tmp/meta_info.txt',
                      '/tmp/process_info.txt',
                      '/tmp/startup_script.txt',
                      '/tmp/error.log',
                      '/tmp/installer.sh']

    if not opts.agent_running:
        files_to_clean.append('/dcm/logs/agent.log')
        files_to_clean.append('/dcm/logs/agent.log.job_runner')
        files_to_clean.append('/dcm/logs/agent.log.wire')
        files_to_clean.append('/dcm/secure/agentdb.sql')

    for f in files_to_clean:
        if os.path.exists(f):
            secure_delete(opts, tar, f)


def general_cleanup(opts, tar):
    console_output(opts, 1, "Performing a general cleanup...")
    files_to_clean = ['/var/lib/waagent/provisioned']

    for f in files_to_clean:
        if os.path.exists(f):
            secure_delete(opts, tar, f)


def clean_dhcp_leases(opts, tar):
    lookfor_strs = ['.*.lease*', '.*.info']
    potential_paths = ['/var/lib/dhcp',
                       '/var/lib/dhcp3',
                       '/var/lib/dhclient',
                       '/var/lib/dhcpcd']
    for p in potential_paths:
        for (dirpath, dirname, filename) in os.walk(p):
            for file in filename:
                found = False
                for lookfor in lookfor_strs:
                    if re.match(lookfor, file):
                        found = True
                        break
                if found:
                    secure_delete(opts, tar, file)


def main(args=sys.argv):
    parser = setup_command_line_parser()
    opts = parser.parse_args(args=args[1:])

    tarfile_path = opts.rescue_tar
    if tarfile_path is None and not opts.batch:
        sys.stdout.write("Please enter the location of the rescue tarfile:")
        sys.stdout.flush()
        tarfile_path = sys.stdin.readline().strip()

    if tarfile_path is not None:
        tarfile_path = os.path.abspath(tarfile_path)
        console_output(opts, 1, "Using the rescue file %s" % tarfile_path)
        tar = tarfile.open(tarfile_path, "w:gz")
    else:
        tar = None

    try:
        if opts.history:
            delete_history(opts, tar)
        if opts.private_keys:
            delete_private_keys(opts, tar)
        if opts.authorized_keys:
            delete_authorize_keys(opts, tar)
        if opts.clean_logs:
            clean_logs(opts, tar)
        if opts.clean_logs:
            clean_dhcp_leases(opts, tar)
        if opts.agent:
            clean_agent_files(opts, tar)
        general_cleanup(opts, tar)
    except BaseException as ex:
        if tar is not None:
            tar.close()
        os.remove(opts.rescue_tar)
        console_output(opts, 0, "Error: " + ex.messsage)
        if opts.verbose > 1:
            raise
        sys.exit(1)
    else:
        if tar is not None:
            tar.close()
            console_output(
                opts, 0,
                _g_tarfile_output_message % tarfile_path)
