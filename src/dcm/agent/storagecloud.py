#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import logging
from libcloud.common.types import LibcloudError

import libcloud.security
from libcloud.storage.types import Provider, ContainerDoesNotExistError
import libcloud.storage.providers as libcloud_providers
from dcm.agent.cloudmetadata import CLOUD_TYPES
from dcm.agent import exceptions


_g_logger = logging.getLogger(__name__)


_map_cloud_id_to_type = {
    1: CLOUD_TYPES.Amazon,
    2: CLOUD_TYPES.Rackspace,
    3: CLOUD_TYPES.Other,
    4: CLOUD_TYPES.Azure,
    5: CLOUD_TYPES.Terremark,
    6: CLOUD_TYPES.Eucalyptus,
    7: CLOUD_TYPES.Eucalyptus,
    8: CLOUD_TYPES.GoGrid,
    9: CLOUD_TYPES.Google,
    10: CLOUD_TYPES.VMware,
    11: CLOUD_TYPES.CloudCentral,
    12: CLOUD_TYPES.ATT,
    13: CLOUD_TYPES.ServerExpress,
    14: CLOUD_TYPES.Amazon,
    15: CLOUD_TYPES.Nimbula,
    16: CLOUD_TYPES.Joyent,
    30: CLOUD_TYPES.CloudSigma,
    33: CLOUD_TYPES.Bluelock,
    34: CLOUD_TYPES.Bluelock,
    20001: CLOUD_TYPES.Other,
    20002: CLOUD_TYPES.Other,
    20013: CLOUD_TYPES.Other
}


def _map_cloud_name_to_provider(cloud_type, region_id):
    map = {
        CLOUD_TYPES.Amazon: {
            "default": Provider.S3,
            "us_west": Provider.S3_US_WEST,
            "us_west_oregon": Provider.S3_US_WEST_OREGON,
            "eu_west": Provider.S3_EU_WEST,
            "ap_southeast": Provider.S3_AP_SOUTHEAST,
            "ap_northeast": Provider.S3_AP_NORTHEAST,
        },
        CLOUD_TYPES.Atmos: None,
        CLOUD_TYPES.ATT: None,
        CLOUD_TYPES.Azure: Provider.AZURE_BLOBS,
        CLOUD_TYPES.Bluelock: None,
        CLOUD_TYPES.CloudCentral: None,
        CLOUD_TYPES.CloudSigma: None,
        CLOUD_TYPES.CloudStack: None,
        CLOUD_TYPES.CloudStack3: None,
        CLOUD_TYPES.Eucalyptus: None,
        CLOUD_TYPES.GoGrid: None,
        CLOUD_TYPES.Google: Provider.GOOGLE_STORAGE,
        CLOUD_TYPES.IBM: None,
        CLOUD_TYPES.Joyent: None,
        CLOUD_TYPES.Nimbula: None,
        CLOUD_TYPES.OpenStack: Provider.OPENSTACK_SWIFT,
        CLOUD_TYPES.Other: None,
        CLOUD_TYPES.Rackspace: None,
        CLOUD_TYPES.ServerExpress: None,
        CLOUD_TYPES.Terremark: None,
        CLOUD_TYPES.VMware: None,
    }

    if cloud_type not in map:
        raise exceptions.AgentUnsupportedCloudFeature()

    provider = map[cloud_type]
    if not provider:
        raise exceptions.AgentUnsupportedCloudFeature()
    if type(provider) == dict:
        if region_id is None:
            region_id = "default"
        if region_id not in provider:
            raise exceptions.AgentUnsupportedCloudFeature()
        provider = provider[region_id]

    return libcloud_providers.get_driver(provider)


def download(cloud_id, container_name, object_name,
             storage_access_key, storage_secret_key,
             destination_file, region_id=None,
             endpoint=None,
             account=None):
    # for now just cast to an int.  in the future we need to turn
    # delegate strings into a libcloud driver TODO
    cloud_id = int(cloud_id)

    try:
        cloud_type = _map_cloud_id_to_type[cloud_id]
        driver_cls = _map_cloud_name_to_provider(cloud_type, region_id)
    except KeyError:
        raise exceptions.AgentUnsupportedCloudFeature()

    try:
        driver = driver_cls(storage_access_key, storage_secret_key)

        obj = driver.get_object(container_name=container_name,
                                object_name=object_name)
        obj.download(destination_path=destination_file)
    except LibcloudError as ex:
        _g_logger.exception(ex)
        raise exceptions.AgentStorageCloudException(str(ex))


def upload(cloud_id,
           source_path,
           container_name,
           object_name,
           storage_access_key,
           storage_secret_key,
           region_id=None,
           endpoint=None,
           account=None):

    try:
        cloud_type = _map_cloud_id_to_type[cloud_id]
        driver_cls = _map_cloud_name_to_provider(cloud_type, region_id)
    except KeyError:
        raise exceptions.AgentUnsupportedCloudFeature()

    driver = driver_cls(storage_access_key, storage_secret_key)

    try:
        container = driver.get_container(container_name)
    except ContainerDoesNotExistError as libCloudEx:
        container = driver.create_container(container_name=container_name)

    driver.upload_object(source_path, container, object_name)


def get_cloud_driver(cloud_id,
                     access_key,
                     secret_key,
                     region_id=None,
                     endpoint=None,
                     account=None):

    cloud_type = _map_cloud_id_to_type[cloud_id]
    driver_cls = _map_cloud_name_to_provider(cloud_type, region_id)

    driver = driver_cls(access_key, secret_key)
    return driver

# libcloud.security.CA_CERTS_PATH.append('/Users/bresnaha/cert')
# libcloud.security.VERIFY_SSL_CERT = False
# driver = libcloud_providers.get_driver(Provider.AZURE_BLOBS)
# d = driver('mediasvcbldtllnf01jhs', secret='syMWzquRwk18IHX31fXTYJ9b6GCou03BNin3rG5/OQKEmuWFvpWXQG0A5NzG485pQ4Q+ZBuruudhlklD3Xy37g==', sercure=False)
# print d.list_containers()