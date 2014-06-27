import ConfigParser
import os
import shutil
import tempfile
import unittest
import yaml

import dcm.agent.cmd.configure as configure
import dcm.agent.tests.utils as test_utils


class TestConfigure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.test_base_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_base_path)

    def test_dir_configure(self):
        conf_args = ["-c", "Amazon",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", self.test_base_path,
                     "-C", "ws"]
        rc = configure.main(conf_args)
        self.assertEqual(rc, 0)

        subdirs_to_check = ["custom", "etc", "home", "logs", "bin",
                            "etc/agent.conf", "etc/logging.yaml",
                            "etc/plugin.conf"]

        for d in subdirs_to_check:
            d = os.path.join(self.test_base_path, d)
            self.assertTrue(os.path.exists(d), d)

    def test_all_cloud_configure(self):
        for cloud in configure.cloud_choices.values():
            conf_args = ["-p", self.test_base_path, "-c", cloud]
            rc = configure.main(conf_args)
            self.assertEqual(rc, 0)

            parser = ConfigParser.SafeConfigParser()
            parser.read(os.path.join(self.test_base_path, "etc", "agent.conf"))

            cloud_from_file = parser.get("cloud", "type")
            self.assertEqual(cloud_from_file.lower(), cloud.lower())

    def test_all_cloud_reconfigure(self):
        url = 'http://someplace.com:2342/hello'
        conf_args = ["-p", self.test_base_path, "-c", "Azure",
                     "-u", url]
        rc = configure.main(conf_args)
        self.assertEqual(rc, 0)

        conf_args = ["-p", self.test_base_path, "-r",
                     os.path.join(self.test_base_path, "etc", "agent.conf"),
                     "-u", url]
        rc = configure.main(conf_args)
        self.assertEqual(rc, 0)

        parser = ConfigParser.SafeConfigParser()
        parser.read(os.path.join(self.test_base_path, "etc", "agent.conf"))

        agentmanager_url = parser.get("connection", "agentmanager_url")
        self.assertEqual(agentmanager_url, url)
