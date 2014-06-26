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
import json
import logging
import os
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


def _get_metadata_server_url_data(url, timeout=1):
    _g_logger.debug("Attempting to get metadata at %s" % url)
    u_req = urllib2.Request(url)
    u_req.add_header("Content-Type", "application/x-www-form-urlencoded")
    u_req.add_header("Connection", "Keep-Alive")
    u_req.add_header("Cache-Control", "no-cache")

    try:
        response = urllib2.urlopen(u_req, timeout=timeout)
    except urllib2.URLError:
        return None
    if response.code != 200:
        return None
    data = response.read().strip()
    return data


def get_dhcp_ip_address(conf):
    if conf.dhcp_address is not None:
        return conf.dhcp_address

    (stdout, stderr, rc) = utils.run_script(conf, "getDhcpAddress", [])
    if rc != 0:
        raise exceptions.AgentExecutableException(
            "getDhcpAddress", rc, stdout, stderr)

    conf.dhcp_address = stdout.strip()
    return conf.dhcp_address


def get_cloud_metadata(conf, key):
    _g_logger.debug("Get metadata %s" % key)

    try:
        result = None
        if conf.cloud_type == CLOUD_TYPES.Amazon or\
                conf.cloud_type == CLOUD_TYPES.Eucalyptus or\
                conf.cloud_type == CLOUD_TYPES.Google:
            if conf.cloud_metadata_url is None:
                _g_logger.warn("The metadata server is None")
                return None
            url = conf.cloud_metadata_url + "/" + key
            data = _get_metadata_server_url_data(url)
            result = data
        elif conf.cloud_type == CLOUD_TYPES.CloudStack or\
                conf.cloud_type == CLOUD_TYPES.CloudStack3:
            addr = get_dhcp_ip_address(conf)
            url = "http://%s/" % addr
            result = _get_metadata_server_url_data(url)
            if result is not None and\
                    conf.cloud_type == CLOUD_TYPES.CloudStack:
                # split the name out for anything before CloudStack 3
                split_name = result.strip().split("-")
                if len(split_name) > 2:
                    result = split_name[2]
        elif conf.cloud_type == CLOUD_TYPES.OpenStack:
            try:
                if conf.cloud_metadata_url is None:
                    _g_logger.warn("The metadata server is None")
                    return None
                url = conf.cloud_metadata_url
                json_data = _get_metadata_server_url_data(url)
                jdict = json.loads(json_data)
                result = jdict[key]
            except:
                _g_logger.exception("Failed to get the OpenStack metadata")
                result = None
        else:
            # NOTE we may want to log this
            result = None
        return result
    finally:
        _g_logger.debug("Metadata value of %s is %s" % (key, result))


def get_instance_id(conf):
    _g_logger.debug("Get instance ID called")

    try:
        if conf.instance_id is not None:
            return conf.instance_id

        if conf.cloud_type == CLOUD_TYPES.Amazon or\
                conf.cloud_type == CLOUD_TYPES.Eucalyptus:
            instance_id = get_cloud_metadata(conf, "instance-id")
        elif conf.cloud_type == CLOUD_TYPES.CloudStack:
            instance_id = get_cloud_metadata(conf, "instance-id")
        elif conf.cloud_type == CLOUD_TYPES.CloudStack3:
            instance_id = get_cloud_metadata(conf, "vm-id")
        elif conf.cloud_type == CLOUD_TYPES.OpenStack:
            instance_id = get_cloud_metadata(conf, "uuid")
        elif conf.cloud_type == CLOUD_TYPES.Google:
            instance_id = get_cloud_metadata(
                conf, "instance/attributes/es-dmcm-launch-id")
        elif conf.cloud_type == CLOUD_TYPES.Azure:
            hostname = socket.gethostname()
            if not hostname:
                return None
            ha = hostname.split(".")
            return "%s:%s:%s" % (ha[0], ha[0], ha[0])
        else:
            instance_id = None
        conf.instance_id = instance_id
    finally:
        _g_logger.debug("Instance ID is %s" % str(conf.instance_id))
    return instance_id


def get_ipv4_addresses(conf):
    # do caching
    ip_list = []
    if conf.cloud_type == CLOUD_TYPES.Amazon or\
            conf.cloud_type == CLOUD_TYPES.Eucalyptus:
        private_ip = get_cloud_metadata(conf, "local-ipv4")
        if private_ip:
            ip_list.append(private_ip)

    (stdout, stderr, rc) = utils.run_script(conf, "getIpAddresses", [])
    for line in stdout.split(os.linesep):
        line = line.strip()
        if line and line not in ip_list:
            ip_list.append(line)
    return ip_list
