import getpass
import os
import platform
import shutil
import socket
import tempfile
import unittest

import nose.plugins.skip as skip

from dcm.agent import cloudmetadata, config
from dcm.agent.cmd import configure
import dcm.agent.tests.utils as test_utils


class TestCloudMetadata(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()
        cls.run_as_user = getpass.getuser()
        cls.test_base_path = tempfile.mkdtemp()
        conf_args = ["-c", "Amazon",
                     "-u", "http://doesntmatter.org/ws",
                     "-m", os.path.join(cls.test_base_path, "mnt"),
                     "-p", cls.test_base_path,
                     "-P", "ubuntu",
                     "-s", os.path.join(cls.test_base_path, "services"),
                     "-t", os.path.join(cls.test_base_path, "tmp"),
                     "-C", "success_tester",
                     "-U", cls.run_as_user,
                     "-l", "/tmp/agent_test_log.log"]
        rc = configure.main(conf_args)
        if rc != 0:
            raise Exception("We could not configure the test env")
        cls.test_conf_path = \
            os.path.join(cls.test_base_path, "etc", "agent.conf")
        cls.conf = config.AgentConfig([cls.test_conf_path])
        cls.conf.start_job_runner()

    @classmethod
    def tearDownClass(cls):
        cls.conf.jr.shutdown()
        shutil.rmtree(cls.test_base_path)

    def setUp(self):
        pass

    def test_dhcp(self):
        ipaddr = cloudmetadata.get_dhcp_ip_address(self.conf)
        if platform.system().lower() == "linux":
            # just verify that it is an ip addr
            pass

    def _get_instance_data_cloud_none(self, cloud):
        self.conf.cloud_type = cloud
        inst_id = cloudmetadata.get_instance_id(self.conf, caching=False)
        self.assertIsNone(inst_id)

    def test_get_instance_data_amazon_none(self):
        if 'DCM_AGENT_ON_AMAZON' in os.environ:
            raise skip.SkipTest("We are actually on amazon")
        self._get_instance_data_cloud_none(cloudmetadata.CLOUD_TYPES.Amazon)

    def test_get_instance_data_eucalyptus_none(self):
        self._get_instance_data_cloud_none(
            cloudmetadata.CLOUD_TYPES.Eucalyptus)

    def test_get_instance_data_cloudstack_none(self):
        self._get_instance_data_cloud_none(
            cloudmetadata.CLOUD_TYPES.CloudStack)

    def test_get_instance_data_cloudstack3_none(self):
        self._get_instance_data_cloud_none(
            cloudmetadata.CLOUD_TYPES.CloudStack3)

    def test_get_instance_data_openstack_none(self):
        self._get_instance_data_cloud_none(cloudmetadata.CLOUD_TYPES.OpenStack)

    def test_get_instance_data_google_none(self):
        self._get_instance_data_cloud_none(cloudmetadata.CLOUD_TYPES.Google)

    def test_get_instance_data_azure_none(self):
        self.conf.cloud_type = cloudmetadata.CLOUD_TYPES.Azure
        inst_id = cloudmetadata.get_instance_id(self.conf, caching=False)
        # this will likely change in the future
        hostname = socket.gethostname()
        ha = hostname.split(".")
        should_be = "%s:%s:%s" % (ha[0], ha[0], ha[0])
        self.assertEqual(should_be, inst_id)
