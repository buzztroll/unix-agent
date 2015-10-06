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
import getpass
import os
import shutil
import tempfile
import unittest

import dcm.agent.cmd.service as service
import dcm.agent.cmd.configure as configure
import dcm.agent.logger as logger
import dcm.agent.tests.utils.general as test_utils


# does not inherit from unittest because of the python generators for
# testing storage clouds

class TestAgentStatus(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.run_as_user = getpass.getuser()
        test_utils.connect_to_debugger()
        cls.test_base_path = tempfile.mkdtemp()
        cls.test_conf_path = os.path.join(
            cls.test_base_path, "etc", "agent.conf")
        conf_args = ["-c", "Amazon",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", cls.test_base_path,
                     "-t", os.path.join(cls.test_base_path, "tmp"),
                     "-C", "ws",
                     "-U", cls.run_as_user,
                     "-l", "/tmp/agent_status_test.log"]
        rc = configure.main(conf_args)
        if rc != 0:
            raise Exception("We could not configure the test env")

    @classmethod
    def tearDownClass(cls):
        logger.clear_dcm_logging()
        shutil.rmtree(cls.test_base_path)

    def test_agent_status(self):
        # we need a way to parse the output to verify tests
        rc = service.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)
