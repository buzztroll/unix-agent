# ========= CONFIDENTIAL =========
#
# Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
# ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import json
import logging
import os
import platform
import socket
import urllib2
from dcm.agent import exceptions

import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class CLOUD_TYPES:
    Amazon = "Amazon"
    Atmos = "Atmos"
    ATT = "ATT"
    Azure = "Azure"
    Bluelock = "Bluelock"
    CloudCentral = "CloudCentral"
    CloudSigma = "CloudSigma"
    CloudStack = "CloudStack"
    CloudStack3 = "CloudStack3"
    Eucalyptus = "Eucalyptus"
    GoGrid = "GoGrid"
    Google = "Google"
    IBM = "IBM"
    Joyent = "Joyent"
    Nimbula = "Nimbula"
    OpenStack = "OpenStack"
    Other = "Other"
    Rackspace = "Rackspace"
    ServerExpress = "ServerExpress"
    Terremark = "Terremark"
    VMware = "VMware"


class CloudMetaData(object):
    def get_cloud_metadata(self, key):
        return None

    def get_instance_id(self):
        _g_logger.debug("Get instance ID called")
        return None

    def get_ipv4_addresses(self, conf):
        ip_list = []
        (stdout, stderr, rc) = utils.run_script(conf, "getIpAddresses", [])
        for line in stdout.split(os.linesep):
            line = line.strip()
            if line and line not in ip_list:
                ip_list.append(line)
        return ip_list

    def get_handshake_ip_address(self, conf):
        return self.get_ipv4_addresses(conf)


class AWSMetaData(CloudMetaData):
    def __init__(self, conf):
        self.conf = conf
        if conf.cloud_metadata_url:
            self.base_url = conf.cloud_metadata_url
        else:
            self.base_url = "http://169.254.169.254/latest/meta-data"

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        url = self.base_url + "/" + key
        result = _get_metadata_server_url_data(url)
        _g_logger.debug("Metadata value of %s is %s" % (key, result))
        return result

    def get_instance_id(self):
        instance_id = self.get_cloud_metadata("instance-id")
        super(AWSMetaData, self).get_instance_id()
        _g_logger.debug("Instance ID is %s" % str(instance_id))
        return instance_id

    def get_ipv4_addresses(self, conf):
        # do caching
        ip_list = []
        private_ip = conf.meta_data_object.get_cloud_metadata("local-ipv4")

        if private_ip:
            ip_list.append(private_ip)

        ip_list_from_base = super(AWSMetaData, self).get_ipv4_addresses(self.conf)
        for ip in ip_list_from_base:
            ip_list.append(ip)

        return ip_list

    def get_handshake_ip_address(self, conf):
        return [conf.meta_data_object.get_cloud_metadata("local-ipv4")]


class JoyentMetaData(CloudMetaData):
    def __init__(self, conf):
        self.conf = conf

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        if platform.version().startswith("Sun"):
            cmd = "/usr/sbin/mdata-get"
        else:
            cmd = "/lib/smartdc/mdata-get"

        cmd_args = ["sudo", cmd, key]
        (stdout, stderr, rc) = utils.run_command(self.conf, cmd_args)
        if rc != 0:
            result = None
        else:
            result = stdout.strip()
        _g_logger.debug("Metadata value of %s is %s" % (key, result))
        return result

    def get_instance_id(self):
        instance_id = self.get_cloud_metadata("es:dmcm-launch-id")
        super(JoyentMetaData, self).get_instance_id()
        _g_logger.debug("Instance ID is %s" % str(instance_id))
        return instance_id


class GCEMetaData(CloudMetaData):
    def __init__(self, conf):
        if conf.cloud_metadata_url:
            self.base_url = conf.cloud_metadata_url
        else:
            self.base_url = "http://metadata.google.internal/computeMetadata/v1"

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        url = self.base_url + "/" + key
        result = _get_metadata_server_url_data(
            url, headers=[("Metadata-Flavor", "Google")])
        _g_logger.debug("Metadata value of %s is %s" % (key, result))
        return result

    def get_instance_id(self):
        instance_id = self.get_cloud_metadata(
            "instance/attributes/es-dmcm-launch-id")
        super(GCEMetaData, self).get_instance_id()
        _g_logger.debug("Instance ID is %s" % str(instance_id))
        return instance_id

    def get_handshake_ip_address(self, conf):
        return [self.get_cloud_metadata(
            "instance/attributes/es-dmcm-launch-id")]


class AzureMetaData(CloudMetaData):
    def get_instance_id(self):
        hostname = socket.gethostname()
        if not hostname:
            return None
        ha = hostname.split(".")
        return "%s:%s:%s" % (ha[0], ha[0], ha[0])


def set_metadata_object(conf):
    if conf.cloud_type == CLOUD_TYPES.Amazon:
        meta_data_obj = AWSMetaData(conf)

    elif conf.cloud_type == CLOUD_TYPES.Joyent:
        meta_data_obj = JoyentMetaData(conf)

    elif conf.cloud_type == CLOUD_TYPES.Google:
        meta_data_obj = GCEMetaData(conf)

    elif conf.cloud_type == CLOUD_TYPES.Azure:
        meta_data_obj = AzureMetaData()

    else:
        meta_data_obj = CloudMetaData()

    conf.meta_data_object = meta_data_obj


def get_dhcp_ip_address(conf):
    if conf.dhcp_address is not None:
        return conf.dhcp_address

    (stdout, stderr, rc) = utils.run_script(conf, "getDhcpAddress", [])
    if rc != 0:
        raise exceptions.AgentExecutableException(
            "getDhcpAddress", rc, stdout, stderr)

    conf.dhcp_address = stdout.strip()
    return conf.dhcp_address


def _get_metadata_server_url_data(url, timeout=1, headers=None):
    if not url:
        return None

    _g_logger.debug("Attempting to get metadata at %s" % url)
    u_req = urllib2.Request(url)
    u_req.add_header("Content-Type", "application/x-www-form-urlencoded")
    u_req.add_header("Connection", "Keep-Alive")
    u_req.add_header("Cache-Control", "no-cache")
    if headers:
        for (h, v) in headers:
            u_req.add_header(h, v)

    try:
        response = urllib2.urlopen(u_req, timeout=timeout)
    except urllib2.URLError:
        return None
    if response.code != 200:
        return None
    data = response.read().strip()
    return data

