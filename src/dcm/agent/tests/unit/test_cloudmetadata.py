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
import shutil
import tempfile
import unittest
import uuid
import mock

import dcm.agent.exceptions as exceptions
import dcm.agent.tests.utils.general as test_utils
import dcm.agent.cloudmetadata as cm


class TestCloudMetaDataBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.conf = mock.Mock()
        self.cm_obj = cm.CloudMetaData(self.conf)

    def test_base_instance_id(self):
        instance_id = self.cm_obj.get_instance_id()
        self.assertIsNone(instance_id)

    def test_base_is_effective(self):
        v = self.cm_obj.is_effective_cloud()
        self.assertFalse(v)

    def test_base_startup(self):
        self.assertRaises(exceptions.AgentNotImplementedException,
                          self.cm_obj.get_startup_script)

    def test_base_get_cloud_type(self):
        self.assertRaises(exceptions.AgentNotImplementedException,
                          self.cm_obj.get_cloud_type)

    def test_env_injected_id_no_env(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            self.conf.get_secure_dir.return_value = tmp_dir
            injected_id = self.cm_obj.get_injected_id()
            self.assertIsNone(injected_id)
        finally:
            shutil.rmtree(tmp_dir)

    def test_env_injected_id_env(self):
        tmp_dir = tempfile.mkdtemp()
        fake_id = str(uuid.uuid4())
        id_file = os.path.join(tmp_dir, "injected_id")

        try:
            self.conf.get_secure_dir.return_value = tmp_dir
            with mock.patch.dict('os.environ',
                                 {cm.ENV_INJECTED_ID_KEY: fake_id}):
                injected_id = self.cm_obj.get_injected_id()
            self.assertEqual(injected_id, fake_id)
            self.assertTrue(os.path.exists(id_file))

            with open(id_file, "r") as fptr:
                v = fptr.read().strip()
            self.assertEqual(v, injected_id)

        finally:
            shutil.rmtree(tmp_dir)

    def test_env_injected_id_env_file_exists(self):
        tmp_dir = tempfile.mkdtemp()
        fake_id = str(uuid.uuid4())
        id_file = os.path.join(tmp_dir, "injected_id")
        try:
            with open(id_file, "w") as fptr:
                fptr.write(fake_id)

            self.conf.get_secure_dir.return_value = tmp_dir
            injected_id = self.cm_obj.get_injected_id()
            self.assertEqual(injected_id, fake_id)
            with open(id_file, "r") as fptr:
                v = fptr.read().strip()
            self.assertEqual(v, injected_id)
        finally:
            shutil.rmtree(tmp_dir)

    def test_ipv4_address(self):
        addr = self.cm_obj.get_ipv4_addresses()
        self.assertEqual(type(addr), list)
        self.assertGreaterEqual(len(addr), 1)

    def test_handshake_address(self):
        addr = self.cm_obj.get_handshake_ip_address()
        self.assertEqual(type(addr), list)
        self.assertGreaterEqual(len(addr), 1)


class TestUnknownMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.UnknownMetaData(conf)

    def test_effective_cloud(self):
        self.assertTrue(self.cm_obj.is_effective_cloud())

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(), cm.CLOUD_TYPES.UNKNOWN)


class TestAWSMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.conf = mock.Mock()
        self.cm_obj = cm.AWSMetaData(self.conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(), cm.CLOUD_TYPES.Amazon)

    @mock.patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_base_startup(self, md_server_data):
        startup_data = "some date"
        md_server_data.return_value = startup_data
        sd = self.cm_obj.get_startup_script()
        self.assertEqual(startup_data, sd)

    @mock.patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_base_injected_id(self, md_server_data):
        fake_id = "somedata"
        md_server_data.return_value = fake_id
        sd = self.cm_obj.get_injected_id()
        self.assertEqual(fake_id, sd)

    @mock.patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_base_injected_id_none(self, md_server_data):
        tmp_dir = tempfile.mkdtemp()
        try:
            self.conf.get_secure_dir.return_value = tmp_dir
            fake_id = None
            md_server_data.return_value = fake_id
            sd = self.cm_obj.get_injected_id()
            self.assertIsNone(sd)
        finally:
            shutil.rmtree(tmp_dir)


class TestCloudStackMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.CloudStackMetaData(conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.CloudStack)


class TestJoyentMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        self.conf = mock.Mock()
        self.cm_obj = cm.JoyentMetaData(self.conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.Joyent)

    @mock.patch('dcm.agent.utils.run_command')
    def test_base_injected_id(self, runcmd):
        fakeid = "someid"
        runcmd.return_value = (fakeid, "", 0)
        x = self.cm_obj.get_injected_id()
        self.assertEqual(fakeid, x)

    @mock.patch('dcm.agent.utils.run_command')
    def test_base_cached_injected_id(self, runcmd):
        fakeid = "someid"
        runcmd.return_value = (fakeid, "", 0)
        x = self.cm_obj.get_injected_id()
        self.assertEqual(fakeid, x)
        x = self.cm_obj.get_injected_id()
        self.assertEqual(fakeid, x)

    @mock.patch('dcm.agent.utils.run_command')
    def test_base_injected_try_both_locations(self, runcmd):
        fakeid = "someid"
        runcmd.return_value = ("", "error", 1)

        tmp_dir = tempfile.mkdtemp()
        try:
            self.conf.get_secure_dir.return_value = tmp_dir
            self.conf.system_sudo = "sudo"
            x = self.cm_obj.get_injected_id()

            call1 = mock.call(
                self.conf,
                ["sudo", "/usr/sbin/mdata-get", "es:dmcm-launch-id"])
            call2 = mock.call(
                self.conf,
                ["sudo", "/lib/smartdc/mdata-get", "es:dmcm-launch-id"])

            self.assertEqual(runcmd.call_args_list, [call1, call2])
            self.assertEqual(runcmd.call_count, 2)
            self.assertIsNone(x)
        finally:
            shutil.rmtree(tmp_dir)


class TestGCEMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.GCEMetaData(conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.Google)


class TestAzureMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.AzureMetaData(conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.Azure)


class TestOpenStackMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.OpenStackMetaData(conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.OpenStack)


class TestKonamiMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.KonamiMetaData(conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.Konami)


class TestDigitalOceanMetaDataBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    def setUp(self):
        conf = mock.Mock()
        self.cm_obj = cm.DigitalOceanMetaData(conf)

    def test_cloud_type(self):
        self.assertEqual(self.cm_obj.get_cloud_type(),
                         cm.CLOUD_TYPES.DigitalOcean)

    @mock.patch('dcm.agent.cloudmetadata._get_metadata_server_url_data')
    def test_base_startup(self, md_server_data):
        startup_data = "some date"
        md_server_data.return_value = startup_data
        sd = self.cm_obj.get_startup_script()
        self.assertEqual(startup_data, sd)
