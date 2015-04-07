import unittest

from dcm.agent import storagecloud as sc
from dcm.agent.exceptions import AgentUnsupportedCloudFeature
import libcloud.security
from libcloud.storage.types import Provider

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

        self.region_map = {
            #maps from regions to actual class names in s3.py
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

        self.assertRaises(AgentUnsupportedCloudFeature,
                          sc.get_cloud_driver,
                          468,
                          'whatever',
                          'whatever')

    def test_get_cloud_driver_raises_exception_type_not_in_map(self):

        self.assertRaises(AgentUnsupportedCloudFeature,
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
