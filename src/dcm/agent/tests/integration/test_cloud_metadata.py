import getpass
import os
import platform
import shutil
import socket
import tempfile
import unittest

from mock import patch
import nose.plugins.skip as skip

import dcm.agent.cloudmetadata as cloudmetadata
import dcm.agent.config as config
import dcm.agent.cmd.configure as configure
import dcm.agent.tests.utils.general as test_utils


class TestCloudMetadata(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()
        cls.run_as_user = getpass.getuser()
        cls.test_base_path = tempfile.mkdtemp()
        conf_args = ["-c", "Amazon",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", cls.test_base_path,
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
        cls.conf.stop_job_runner()
        shutil.rmtree(cls.test_base_path)

    def setUp(self):
        self.clouds = {
            1: cloudmetadata.AWSMetaData,
            2: cloudmetadata.JoyentMetaData,
            3: cloudmetadata.GCEMetaData,
            4: cloudmetadata.AzureMetaData
        }

        self.cloud_types = {
            1: 'Amazon',
            2: 'Joyent',
            3: 'Google',
            4: 'Azure'
        }

    def tearDown(self):
        self.clouds = None
        self.cloud_types = None

    def test_dhcp(self):
        ipaddr = cloudmetadata.get_dhcp_ip_address(self.conf)
        if platform.system().lower() == "linux":
            if not ipaddr:
                self.fail("We could not find the DHCP server address.  "
                          "This will cause CloudStack to fail.")
            try:
                socket.inet_aton(ipaddr)
                self.assertTrue(True)
            except socket.error:
                self.fail('You passed an invalid ip address')

    def _get_instance_data_cloud_none(self, cloud):
        self.conf.cloud_type = cloud
        inst_id = self.conf.meta_data_object.get_instance_id()
        self.assertIsNone(inst_id)

    def test_get_instance_data_amazon_none(self):
        if 'DCM_AGENT_ON_AMAZON' in os.environ:
            raise skip.SkipTest("We are actually on amazon")
        self._get_instance_data_cloud_none(cloudmetadata.CLOUD_TYPES.Amazon)

    def test_get_instance_data_google_none(self):
        self.conf.meta_data_object = cloudmetadata.GCEMetaData(
            self.conf, base_url=self.conf.cloud_metadata_url)
        self._get_instance_data_cloud_none(cloudmetadata.CLOUD_TYPES.Google)

    def test_get_instance_data_joyent_none(self):
        self.conf.meta_data_object = cloudmetadata.JoyentMetaData(self.conf)
        self._get_instance_data_cloud_none(cloudmetadata.CLOUD_TYPES.Joyent)

    def test_get_instance_data_azure_none(self):
        self.conf.cloud_type = cloudmetadata.CLOUD_TYPES.Azure
        self.conf.meta_data_object = cloudmetadata.AzureMetaData(self.conf)
        inst_id = self.conf.meta_data_object.get_instance_id()
        # this will likely change in the future
        hostname = socket.gethostname()
        ha = hostname.split(".")
        should_be = "%s:%s:%s" % (ha[0], ha[0], ha[0])
        self.assertEqual(should_be, inst_id)

    @patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_get_aws_instance_id(self, mock_server):
        self.conf.meta_data_object = cloudmetadata.AWSMetaData(
            self.conf, base_url=self.conf.cloud_metadata_url)
        mock_server.return_value = 'fake_instance_id'
        instance_id = self.conf.meta_data_object.get_instance_id()
        self.assertEqual(instance_id, 'fake_instance_id')

    @patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_get_gce_instance_id(self, mock_server):
        self.conf.meta_data_object = cloudmetadata.GCEMetaData(
            self.conf, base_url=self.conf.cloud_metadata_url)
        mock_server.return_value = 'fake_instance_id'
        instance_id = self.conf.meta_data_object.get_instance_id()
        self.assertEqual(instance_id, 'fake_instance_id')

    @patch('dcm.agent.cloudmetadata.JoyentMetaData.get_cloud_metadata')
    def test_get_joyent_instance_id(self, mock_joyent_meta):
        self.conf.meta_data_object = cloudmetadata.JoyentMetaData(self.conf)
        mock_joyent_meta.return_value = 'fake_instance_id'
        instance_id = self.conf.meta_data_object.get_instance_id()
        self.assertEqual(instance_id, 'fake_instance_id')

    @patch('dcm.agent.cloudmetadata.AzureMetaData.get_instance_id')
    def test_get_azure_instance_id(self, mock_instance_id):
        self.conf.meta_data_object = cloudmetadata.AzureMetaData(self.conf)
        mock_instance_id.return_value =\
            'fake_instance_id:fake_instance_id:fake_instance_id'
        instance_id = self.conf.meta_data_object.get_instance_id()
        self.assertEqual(instance_id,
                         'fake_instance_id:fake_instance_id:fake_instance_id')

    @patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_get_aws_startup_script(self, mock_server):
        self.conf.meta_data_object = cloudmetadata.AWSMetaData(
            self.conf, base_url=self.conf.cloud_metadata_url)
        mock_server.return_value = 'fake_startup_script'
        script = self.conf.meta_data_object.get_startup_script()
        self.assertEqual(script, 'fake_startup_script')

    @patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_get_gce_startup_script(self, mock_server):
        self.conf.meta_data_object = cloudmetadata.GCEMetaData(
            self.conf, base_url=self.conf.cloud_metadata_url)
        mock_server.return_value = 'fake_startup_script'
        script = self.conf.meta_data_object.get_startup_script()
        self.assertEqual(script, 'fake_startup_script')

    @patch('dcm.agent.cloudmetadata.JoyentMetaData.get_cloud_metadata')
    def test_get_joyent_startup_script(self, mock_joyent_meta):
        self.conf.meta_data_object = cloudmetadata.JoyentMetaData(self.conf)
        mock_joyent_meta.return_value = 'fake_startup_script'
        script = self.conf.meta_data_object.get_startup_script()
        self.assertEqual(script, 'fake_startup_script')

    @patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_get_openstack_startup_script(self, mock_cloud_meta):
        self.conf.meta_data_object = cloudmetadata.OpenStackMetaData(self.conf)
        mock_cloud_meta.return_value = 'fake_startup_script'
        script = self.conf.meta_data_object.get_startup_script()
        self.assertEqual(script, 'fake_startup_script')

    def test_set_metadata_object(self):
        for cloud in self.clouds:
            self.conf.cloud_type = self.cloud_types[cloud]
            self.conf.meta_data_object = None
            cloudmetadata.set_metadata_object(self.conf)
            self.assertIsInstance(self.conf.meta_data_object,
                                  self.clouds[cloud])
