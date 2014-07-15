import getpass
import os
import shutil
import tempfile
import nose

import dcm.agent.cmd.service as service
import dcm.agent.cmd.configure as configure
import dcm.agent.logger as logger
import dcm.agent.tests.utils as test_utils


# does not inherit from unittest because of the python generators for
# testing storage clouds
class TestAgentStatus(object):

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
                     "-s", os.path.join(cls.test_base_path, "services"),
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
        nose.tools.eq_(rc, 1)
