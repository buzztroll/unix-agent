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
import unittest
import os
import threading
import dcm.agent.tests.utils.general as test_utils

from dcm.agent.ossec import OssecAlertParser

TEST_STRING="""
** Alert 1446578476.4335: - syslog,sshd,authentication_success,
2015 Nov 03 19:21:16 vagrant->/var/log/auth.log
Rule: 5715 (level 3) -> 'SSHD authentication success.'
Src IP: 10.0.2.2
User: vagrant
Nov  3 19:21:16 vagrant sshd[19258]: Accepted publickey for vagrant from 10.0.2.2 port 54086 ssh2: RSA dd:3b:b8:2e:85:04:06:e9:ab:ff:a8:0a:c0:04:6e:d6

** Alert 1446578476.4685: - pam,syslog,authentication_success,
2015 Nov 03 19:21:16 vagrant->/var/log/auth.log
Rule: 5501 (level 3) -> 'Login session opened.'
Nov  3 19:21:16 vagrant sshd[19258]: pam_unix(sshd:session): session opened for user vagrant by (uid=0)

** Alert 1446578480.4949: - syslog,sudo
2015 Nov 03 19:21:20 vagrant->/var/log/auth.log
Rule: 5402 (level 3) -> 'Successful sudo to ROOT executed'
User: vagrant
Nov  3 19:21:18 vagrant sudo:  vagrant : TTY=pts/1 ; PWD=/home/vagrant ; USER=root ; COMMAND=/bin/bash

** Alert 1446578480.5214: - pam,syslog,authentication_success,
2015 Nov 03 19:21:20 vagrant->/var/log/auth.log
Rule: 5501 (level 3) -> 'Login session opened.'
Nov  3 19:21:18 vagrant sudo: pam_unix(sudo:session): session opened for user root by vagrant(uid=0)
"""

class TestOssec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()
        cls.oap = OssecAlertParser(dir_to_watch='/tmp')
        t = threading.Thread(target=cls.oap.start).start()

    def setUp(self):
        pass

    def test_parse_data(self):
        with open("/tmp/alerts.log", 'a') as f:
            f.write(TEST_STRING)
        os.system('touch /tmp/alerts.log')
