import ConfigParser
import os
import shutil
import tempfile
import unittest
from dcm.agent import cloudmetadata
import mock
import sys
import dcm

import dcm.agent.cmd.configure as configure
import dcm.agent.tests.utils.general as test_utils


class TestConfigure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.test_base_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_base_path)

    def test_cloud_name_case(self):
        conf_args = ["-c", "aMazOn",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", self.test_base_path,
                     "-C", "ws"]
        rc = configure.main(conf_args)
        self.assertEqual(rc, 0)

        parser = ConfigParser.SafeConfigParser()
        parser.read(os.path.join(self.test_base_path, "etc", "agent.conf"))
        cloud_from_file = parser.get("cloud", "type")
        self.assertEqual(cloudmetadata.CLOUD_TYPES.Amazon, cloud_from_file)

    def test_cloud_name_bad(self):
        conf_args = ["-c", "NoGood",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", self.test_base_path,
                     "-C", "ws"]
        self.assertRaises(Exception, configure.main, conf_args)

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
        for cloud in configure.cloud_choices:
            conf_args = ["-p", self.test_base_path, "-c", cloud]
            rc = configure.main(conf_args)
            self.assertEqual(rc, 0)

            parser = ConfigParser.SafeConfigParser()
            parser.read(os.path.join(self.test_base_path, "etc", "agent.conf"))

            cloud_from_file = parser.get("cloud", "type")
            self.assertEqual(cloud_from_file.lower(), cloud.lower())

            try:
                cloud_from_file = parser.get("cloud", "metadata_url")
            except:
                cloud_from_file = None
            if cloud == "Amazon":
                mu = "http://169.254.169.254/latest/meta-data/"
                self.assertEqual(mu, cloud_from_file)
            elif cloud == "Eucalyptus":
                mu = "http://169.254.169.254/1.0/meta-data/"
                self.assertEqual(mu, cloud_from_file)
            elif cloud == "OpenStack":
                mu = "http://169.254.169.254/openstack/2012-08-10/meta_data.json"
                self.assertEqual(mu, cloud_from_file)
            elif cloud == "Google":
                mu = "http://metadata.google.internal/computeMetadata/v1"
                self.assertEqual(mu, cloud_from_file)
            elif cloud == "CloudStack":
                self.assertIsNone(cloud_from_file)
            elif cloud == "CloudStack3":
                self.assertIsNone(cloud_from_file)
            else:
                self.assertIsNone(cloud_from_file)

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

    def test_configure_get_url(self):
        url = "ws://someplace.com:5434/path"
        with mock.patch('sys.stdin'):
            sys.stdin.readline.return_value = url
            x = configure.get_url()
        self.assertEqual(x, url)

    def test_configure_get_url_bad_scheme(self):
        url = "notgood://someplace.com:5434/path"
        with mock.patch('sys.stdin'):
            sys.stdin.readline.return_value = url
            self.assertRaises(Exception, configure.get_url)

    def test_configure_get_url_bad_url(self):
        url = "sdkfjlkjrewlkjrewl"
        with mock.patch('sys.stdin'):
            sys.stdin.readline.return_value = url
            self.assertRaises(Exception, configure.get_url)

    def test_configure_cloud_choice(self):
        cloud_choice = "1"
        with mock.patch('dcm.agent.cmd.configure._get_input'):
            configure._get_input.return_value = cloud_choice
            cloud = configure.select_cloud()
        self.assertEqual(cloud.lower(), "amazon")

    def test_configure_bad_cloud_choice(self):
        aws = ["bad", "1"]

        def _l_get_input(prompt):
            return aws.pop()

        func = dcm.agent.cmd.configure._get_input
        try:
            dcm.agent.cmd.configure._get_input = _l_get_input
            cloud = configure.select_cloud()
        finally:
            dcm.agent.cmd.configure._get_input = func
        self.assertEqual(cloud.lower(), "amazon")

    def test_interactive_configure(self):
        def _l_get_input(prompt):
            return "12"

        url = "ws://someplace.com:5434/path"
        with mock.patch('sys.stdin'):
            sys.stdin.readline.return_value = url

            func = dcm.agent.cmd.configure._get_input
            try:
                dcm.agent.cmd.configure._get_input = _l_get_input
                conf_args = ["-p", self.test_base_path,
                             "-C", "ws",
                             "-i"]
                rc = configure.main(conf_args)
            finally:
                dcm.agent.cmd.configure._get_input = func

        self.assertEqual(rc, 0)

        parser = ConfigParser.SafeConfigParser()
        parser.read(os.path.join(self.test_base_path, "etc", "agent.conf"))

        agentmanager_url = parser.get("connection", "agentmanager_url")
        self.assertEqual(agentmanager_url, url)
        cloud_type = parser.get("cloud", "type")
        self.assertEqual(cloud_type, "Google")
