# ========= CONFIDENTIAL =========
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
    35: CLOUD_TYPES.OpenStack,
    20001: CLOUD_TYPES.Other,
    20002: CLOUD_TYPES.Other,
    20013: CLOUD_TYPES.Other
}


def _no_driver_function(storage_access_key,
                        storage_secret_key,
                        region_id=None,
                        endpoint=None,
                        account=None,
                        **kwargs):
    raise exceptions.AgentUnsupportedCloudFeature()


def _aws_driver_function(storage_access_key,
                         storage_secret_key,
                         region_id=None,
                         endpoint=None,
                         account=None,
                         **kwargs):
    region_map = {
        "default": Provider.S3,
        "us_west": Provider.S3_US_WEST,
        "us_west_oregon": Provider.S3_US_WEST_OREGON,
        "eu_west": Provider.S3_EU_WEST,
        "ap_southeast": Provider.S3_AP_SOUTHEAST,
        "ap_northeast": Provider.S3_AP_NORTHEAST,
    }

    try:
        provider = region_map[region_id]
    except KeyError:
        provider = Provider.S3

    driver_cls = libcloud_providers.get_driver(provider)
    driver = driver_cls(storage_access_key, storage_secret_key)
    return driver


def _gce_driver_function(storage_access_key,
                         storage_secret_key,
                         region_id=None,
                         endpoint=None,
                         account=None,
                         **kwargs):
    provider = Provider.GOOGLE_STORAGE
    driver_cls = libcloud_providers.get_driver(provider)
    driver = driver_cls(storage_access_key, storage_secret_key)
    return driver


def _azure_driver_function(storage_access_key,
                           storage_secret_key,
                           region_id=None,
                           endpoint=None,
                           account=None,
                           **kwargs):
    provider = Provider.AZURE_BLOBS
    driver_cls = libcloud_providers.get_driver(provider)
    driver = driver_cls(storage_access_key, storage_secret_key)
    return driver


def _openstack_driver_function(storage_access_key,
                               storage_secret_key,
                               region_id=None,
                               endpoint=None,
                               account=None,
                               **kwargs):
    provider = Provider.OPENSTACK_SWIFT
    driver_cls = libcloud_providers.get_driver(provider)
    driver = driver_cls(storage_access_key, storage_secret_key)
    return driver


def _map_cloud_name_to_provider(cloud_type,
                                storage_access_key,
                                storage_secret_key,
                                region_id=None,
                                endpoint=None,
                                account=None,
                                **kwargs):
    cloud_map = {
        CLOUD_TYPES.Amazon: _aws_driver_function,
        CLOUD_TYPES.Azure: _azure_driver_function,
        CLOUD_TYPES.Google: _gce_driver_function,
        CLOUD_TYPES.OpenStack: _openstack_driver_function
    }

    if cloud_type not in cloud_map:
        func = _no_driver_function

    else:
        func = cloud_map[cloud_type]

    driver = func(storage_access_key,
                  storage_secret_key,
                  region_id,
                  endpoint,
                  account,
                  **kwargs)

    return driver


def download(cloud_id,
             container_name,
             object_name,
             storage_access_key,
             storage_secret_key,
             destination_file,
             region_id=None,
             endpoint=None,
             account=None,
             **kwargs):
    # for now just cast to an int.  in the future we need to turn
    # delegate strings into a libcloud driver TODO
    cloud_id = int(cloud_id)

    try:
        cloud_type = _map_cloud_id_to_type[cloud_id]
        driver = _map_cloud_name_to_provider(cloud_type,
                                             storage_access_key,
                                             storage_secret_key,
                                             region_id=region_id,
                                             endpoint=endpoint,
                                             account=account,
                                             **kwargs)

    except KeyError:
        raise exceptions.AgentUnsupportedCloudFeature()

    try:
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
           account=None,
           **kwargs):
    # for now just cast to an int.  in the future we need to turn
    # delegate strings into a libcloud driver TODO
    try:
        cloud_id = int(cloud_id)
    except ValueError:
        pass

    try:
        cloud_type = _map_cloud_id_to_type[cloud_id]
        driver = _map_cloud_name_to_provider(cloud_type,
                                             storage_access_key,
                                             storage_secret_key,
                                             region_id=region_id,
                                             endpoint=endpoint,
                                             account=account,
                                             **kwargs)

    except KeyError:
        raise exceptions.AgentUnsupportedCloudFeature()

    try:
        container = driver.get_container(container_name)
    except ContainerDoesNotExistError as libCloudEx:
        container = driver.create_container(container_name=container_name)

    driver.upload_object(source_path, container, object_name)


def get_cloud_driver(cloud_id,
                     access_key,
                     secret_access_key,
                     region_id=None,
                     endpoint=None,
                     account=None,
                     **kwargs):
    if cloud_id in _map_cloud_id_to_type:
        cloud_type = _map_cloud_id_to_type[cloud_id]
    else:
        raise exceptions.AgentUnsupportedCloudFeature()

    driver_cls = _map_cloud_name_to_provider(cloud_type,
                                             access_key,
                                             secret_access_key,
                                             region_id=region_id,
                                             endpoint=endpoint,
                                             account=account,
                                             **kwargs)
    return driver_cls
