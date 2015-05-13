import os
import pwd


def is_privatekey(keyfile):
    with open(keyfile, 'r') as f:
        if f.readline() == '-----BEGIN RSA PRIVATE KEY-----\n':
            return True
    return False


def main(bin_path):
    all_users = pwd.getpwall()
    user_homes = [user_home[5] for user_home in all_users]
    ssh_dirs = [os.path.join(home_dir, '.ssh') for home_dir in user_homes
                if os.path.isdir(os.path.join(home_dir, '.ssh'))]
    for ssh_dir in ssh_dirs:
        for (dirpath, dirname, filenames) in os.walk(ssh_dir):
            for file in filenames:
                filepath = os.path.join(dirpath, file)
                if is_privatekey(filepath):
                    cmd = '%s %s' % \
                        (os.path.join(bin_path, 'secureDelete'),
                        filepath)
                    os.system(cmd)

if __name__ == "__main__":
    bin_path = os.path.dirname(os.path.abspath(__file__))
    main(bin_path)
