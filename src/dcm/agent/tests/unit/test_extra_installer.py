import logging
import os
import shutil
import tempfile
import unittest
from nose.plugins import skip
from dcm.agent import config

import dcm.agent.cmd.configure as configure
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
        if 'DCM_AGENT_TEST_EXTRA_PACKAGE_URL' not in os.environ:
            raise skip.SkipTest("No extras package known, skipping")
        conf_args = ["-c", "aMazOn",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", self.test_base_path,
                     "-C", "ws",
                     "--install-extras",
                     "--extra-package-location",
                     os.environ['DCM_AGENT_TEST_EXTRA_PACKAGE_URL']]
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