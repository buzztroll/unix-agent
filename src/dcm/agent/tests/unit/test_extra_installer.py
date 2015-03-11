import logging
import os
import shutil
import tempfile
import unittest
from dcm.agent import config, cloudmetadata

import dcm.agent.cmd.configure as configure
from dcm.agent.cmd.service import get_config_files
import dcm.agent.tests.utils.general as test_utils
import dcm.agent.utils as agent_utils


class TestExtraConfigure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()
        cls.conf = config.AgentConfig([])

    def setUp(self):
        self.test_base_path = tempfile.mkdtemp()

        if test_utils.SYSTEM_CHANGING_TEST_ENV not in os.environ:
            return
        try:
            agent_utils.extras_remove(self.conf)
        except Exception as ex:
            logging.exception("Failed to remove extras package, NBD")

    def tearDown(self):
        shutil.rmtree(self.test_base_path)

        if test_utils.SYSTEM_CHANGING_TEST_ENV not in os.environ:
            return
        try:
            agent_utils.extras_remove(self.conf)
        except Exception as ex:
            logging.exception("Failed to remove extras package, NBD")


    @test_utils.system_changing
    def test_config_works_with_install_extras(self):
        conf_args = ["-c", "aMazOn",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", self.test_base_path,
                     "-C", "ws",
                     "--install-extras",
                     "--extra-package-location", "http://dcmagentnightly.s3.amazonaws.com/"]
        rc = configure.main(conf_args)
        self.assertEqual(rc, 0)

    @test_utils.system_changing
    def test_config_works_bad_location(self):
        conf_args = ["-c", "aMazOn",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", self.test_base_path,
                     "-C", "ws",
                     "--install-extras",
                     "--extra-package-location", "http://nogood.something.x/"]
        rc = configure.main(conf_args)
        self.assertNotEqual(rc, 0)
