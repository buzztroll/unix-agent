#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
