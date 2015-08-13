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

import libcloud.security

import dcm.agent.exceptions as exceptions
import dcm.agent.storagecloud as sc

# ok to bypass for testing purposes since passing nonsense creds
libcloud.security.VERIFY_SSL_CERT = False


class TestStorageCloud(unittest.TestCase):

    def setUp(self):
        self.cloud_name_map = {
            1: 'libcloud.storage.drivers.s3',
            4: 'libcloud.storage.drivers.azure_blobs',
            9: 'libcloud.storage.drivers.google_storage',
            35: 'libcloud.storage.drivers.cloudfiles'
        }

        # maps from regions to actual class names in s3.py
        self.region_map = {
            "default": 'S3StorageDriver',
            "us_west": 'S3USWestStorageDriver',
            "us_west_oregon": 'S3USWestOregonStorageDriver',
            "eu_west": 'S3EUWestStorageDriver',
            "ap_southeast": 'S3APSEStorageDriver',
            "ap_northeast": 'S3APNEStorageDriver'
        }

    def tearDown(self):
        self.cloud_name_map = None
        self.region_map = None

    def test_get_cloud_driver_returns_expected(self):

        for key in self.cloud_name_map:
            cloud_driver = sc.get_cloud_driver(
                key,
                'whatever',
                'ij;oh;ojoj;ljlkhjtdoesnotmatter')

            assert (cloud_driver.__module__ == self.cloud_name_map[key])

    def test_get_cloud_driver_raises_exception_for_wrong_id(self):

        self.assertRaises(exceptions.AgentUnsupportedCloudFeature,
                          sc.get_cloud_driver,
                          468,
                          'whatever',
                          'whatever')

    def test_get_cloud_driver_raises_exception_type_not_in_map(self):

        self.assertRaises(exceptions.AgentUnsupportedCloudFeature,
                          sc.get_cloud_driver,
                          10,
                          'whatever',
                          'whatever')

    def test_that_aws_driver_function_picks_correct_driver_based_on_regionid(
            self):

        for key in self.region_map:
            cloud_driver = sc.get_cloud_driver(
                1,
                'whatever',
                'ij;oh;ojoj;ljlkhjtdoesnotmatter',
                region_id=key)

            assert (cloud_driver.__class__.__name__ == self.region_map[key])

    def test_that_aws_driver_function_picks_default_region_on_bogus_region_id(
            self):

        cloud_driver = sc.get_cloud_driver(1,
                                           'whatever',
                                           'whatever',
                                           region_id='fakeregionid')

        assert (cloud_driver.__class__.__name__ == 'S3StorageDriver')
