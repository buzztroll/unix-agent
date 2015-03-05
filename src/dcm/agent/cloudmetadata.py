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
#    Atmos = "Atmos"
#    ATT = "ATT"
    Azure = "Azure"
    Bluelock = "Bluelock"
#    CloudCentral = "CloudCentral"
#    CloudSigma = "CloudSigma"
    CloudStack = "CloudStack"
    CloudStack3 = "CloudStack3"
    Eucalyptus = "Eucalyptus"
#    GoGrid = "GoGrid"
    Google = "Google"
#    IBM = "IBM"
    Joyent = "Joyent"
    Konami = "Konami"
#    Nimbula = "Nimbula"
    OpenStack = "OpenStack"
    Other = "Other"
#    Rackspace = "Rackspace"
#    ServerExpress = "ServerExpress"
#    Terremark = "Terremark"
    UNKNOWN = "UNKNOWN"
#    VMware = "VMware"


def normalize_cloud_name(cloud_name):
    for key in [i for i in dir(CLOUD_TYPES)
                if not i.startswith("_")]:
        name = getattr(CLOUD_TYPES, key)
        if name.lower() == cloud_name.lower():
            return name
    return None


class CloudMetaData(object):
    def get_cloud_metadata(self, key):
        return None

    def get_instance_id(self):
        _g_logger.debug("Get instance ID called")
        return None

    def get_startup_script(self):
        raise exceptions.AgentNotImplementedException("get_startup_script")

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

    def is_effective_cloud(self):
        try:
            tst = self.get_instance_id()
            return tst is not None
        except:
            return False
        return True

    def get_cloud_type(self):
        raise exceptions.AgentNotImplementedException("get_cloud_type")


class UnknownMetaData(CloudMetaData):
    def is_effective_cloud(self):
        return True

    def get_cloud_type(self):
        return CLOUD_TYPES.UNKNOWN


class AWSMetaData(CloudMetaData):
    def __init__(self, base_url=None):
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = "http://169.254.169.254/latest/meta-data"

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        url = self.base_url + "/" + key
        result = _get_metadata_server_url_data(url)
        _g_logger.debug("Metadata value of %s is %s" % (key, result))
        return result

    def get_startup_script(self):
        url = "http://169.254.169.254/latest/user-data"
        _g_logger.debug("Get user-data %s" % url)
        result = _get_metadata_server_url_data(url)
        _g_logger.debug("user-data: %s" % result)
        return result

    def get_instance_id(self):
        instance_id = self.get_cloud_metadata("instance-id")
        super(AWSMetaData, self).get_instance_id()
        _g_logger.debug("Instance ID is %s" % str(instance_id))
        return instance_id

    def get_ipv4_addresses(self, conf):
        # do caching
        ip_list = []
        private_ip = self.get_cloud_metadata("local-ipv4")

        if private_ip:
            ip_list.append(private_ip)

        ip_list_from_base =\
            super(AWSMetaData, self).get_ipv4_addresses(conf)
        for ip in ip_list_from_base:
            ip_list.append(ip)

        return ip_list

    def get_handshake_ip_address(self, conf):
        return [self.get_cloud_metadata("local-ipv4")]

    def get_cloud_type(self):
        return CLOUD_TYPES.Amazon


class CloudStackMetaData(CloudMetaData):
    def __init__(self, conf, base_url=None):
        _g_logger.debug("Using CloudStack")
        self.conf = conf
        self.base_url = base_url

    def _set_metadata_url(self):
        if not self.base_url:
            dhcp_addr = get_dhcp_ip_address(self.conf)
            self.base_url = "http://" + dhcp_addr
        _g_logger.debug("The CloudStack metadata server is " + self.base_url)

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        self._set_metadata_url()
        url = self.base_url + "/" + key
        result = _get_metadata_server_url_data(url)
        _g_logger.debug("Metadata value of %s is %s" % (key, result))
        return result

    def get_instance_id(self):
        self._set_metadata_url()
        instance_id = self.get_cloud_metadata("latest/instance-id")
        super(CloudStackMetaData, self).get_instance_id()
        _g_logger.debug("Instance ID is %s" % str(instance_id))
        return instance_id

    def get_cloud_type(self):
        return CLOUD_TYPES.CloudStack


class JoyentMetaData(CloudMetaData):
    def __init__(self, conf):
        self.conf = conf

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        if platform.version().startswith("Sun"):
            cmd = "/usr/sbin/mdata-get"
        else:
            cmd = "/lib/smartdc/mdata-get"

        cmd_args = ["/usr/bin/sudo", cmd, key]
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

    def get_startup_script(self):
        return self.get_cloud_metadata("user-script")

    def get_cloud_type(self):
        return CLOUD_TYPES.Joyent


class GCEMetaData(CloudMetaData):
    def __init__(self, base_url=None):
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url =\
                "http://metadata.google.internal/computeMetadata/v1"

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get metadata %s" % key)
        url = self.base_url + "/" + key
        result = _get_metadata_server_url_data(
            url, headers=[("Metadata-Flavor", "Google")])
        _g_logger.debug("Metadata value of %s is %s" % (key, result))
        return result

    def get_startup_script(self):
        return self.get_cloud_metadata("instance/attributes/startup-script")

    def get_instance_id(self):
        instance_id = self.get_cloud_metadata(
            "instance/attributes/es-dmcm-launch-id")
        super(GCEMetaData, self).get_instance_id()
        _g_logger.debug("Instance ID is %s" % str(instance_id))
        return instance_id

    def get_handshake_ip_address(self, conf):
        return [self.get_cloud_metadata(
            "instance/attributes/es-dmcm-launch-id")]

    def get_cloud_type(self):
        return CLOUD_TYPES.Google


class AzureMetaData(CloudMetaData):
    def get_instance_id(self):
        hostname = socket.gethostname()
        if not hostname:
            return None
        ha = hostname.split(".")
        return "%s:%s:%s" % (ha[0], ha[0], ha[0])

    def is_effective_cloud(self):
        pass

    def get_cloud_type(self):
        return CLOUD_TYPES.Azure


class OpenStackMetaData(CloudMetaData):
    def __init__(self, base_url=None):
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url =\
                "http://169.254.169.254/openstack/2012-08-10/meta_data.json"

    def get_cloud_metadata(self, key):
        _g_logger.debug("Get OpenStack metadata %s" % key)

        try:
            json_data = _get_metadata_server_url_data(self.base_url)
            jdict = json.loads(json_data)
            return jdict[key]
        except:
            _g_logger.exception("Failed to get the OpenStack metadata")
            return None

    def get_startup_script(self):
        url = "http://169.254.169.254/openstack/2012-08-10/user_data"
        return _get_metadata_server_url_data(url)

    def get_instance_id(self):
        return self.get_cloud_metadata("uuid")

    def get_cloud_type(self):
        return CLOUD_TYPES.OpenStack


class KonamiMetaData(CloudMetaData):
    def get_cloud_metadata(self, key):
        env_str = "DCM_KONAMI_%s" % key
        try:
            return os.environ[env_str]
        except:
            return None

    def get_instance_id(self):
        return self.get_cloud_metadata("INSTANCE_ID")

    def get_handshake_ip_address(self, conf):
        private = self.get_cloud_metadata("PRIVATE_IP")
        public = self.get_cloud_metadata("PUBLIC_IP")
        return [private, public]

    def get_cloud_type(self):
        return CLOUD_TYPES.Konami


def set_metadata_object(conf):
    cloud_name = normalize_cloud_name(conf.cloud_type)

    if cloud_name == CLOUD_TYPES.Amazon:
        meta_data_obj = AWSMetaData(base_url=conf.cloud_metadata_url)
    elif cloud_name == CLOUD_TYPES.Joyent:
        meta_data_obj = JoyentMetaData(conf)
    elif cloud_name == CLOUD_TYPES.Google:
        meta_data_obj = GCEMetaData(base_url=conf.cloud_metadata_url)
    elif cloud_name == CLOUD_TYPES.Azure:
        meta_data_obj = AzureMetaData()
    elif cloud_name == CLOUD_TYPES.OpenStack:
        meta_data_obj = OpenStackMetaData(base_url=conf.cloud_metadata_url)
    elif cloud_name == CLOUD_TYPES.CloudStack or \
            cloud_name == CLOUD_TYPES.CloudStack3:
        meta_data_obj = CloudStackMetaData(
            conf, base_url=conf.cloud_metadata_url)
    elif cloud_name == CLOUD_TYPES.Konami:
        meta_data_obj = KonamiMetaData()
    elif cloud_name == CLOUD_TYPES.Other:
        meta_data_obj = UnknownMetaData()
    else:
        meta_data_obj = CloudMetaData()

    _g_logger.debug("Metadata comes from " + str(meta_data_obj))

    conf.meta_data_object = meta_data_obj


def guess_effective_cloud(conf):
    # it is important to clouds that clone AWS behavior but also have their
    # own behavior before AWS (eg: OpenStack).  Some clouds cannot be
    # guessed (eg: Azure)
    ordered_list_of_clouds = [
        JoyentMetaData(conf),
        OpenStackMetaData(),
        CloudStackMetaData(conf),
        AWSMetaData(),
        GCEMetaData(),
        UnknownMetaData()
    ]
    for md in ordered_list_of_clouds:
        if md.is_effective_cloud():
            return md.get_cloud_type()
    return CLOUD_TYPES.UNKNOWN


def get_dhcp_ip_address(conf):
    if conf.dhcp_address is not None:
        return conf.dhcp_address

    (stdout, stderr, rc) = utils.run_script(conf, "getDhcpAddress", [])
    if rc != 0:
        raise exceptions.AgentExecutableException(
            "getDhcpAddress", rc, stdout, stderr)

    conf.dhcp_address = stdout.strip()
    return conf.dhcp_address


def _get_metadata_server_url_data(url, timeout=10, headers=None):
    if not url:
        _g_logger.debug("URL is  %s" % url)
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
        _g_logger.debug("URL error message is %s" % urllib2.URLError.message)
        return None
    if response.code != 200:
        _g_logger.debug("URL response code is %s" % str(response.code))
        return None
    data = response.read().strip()
    return data
