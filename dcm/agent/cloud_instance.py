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
import urllib2

import dcm.agent.util as util


class CLOUD_TYPES:
    Amazon = "AWS"
    Eucalyptus = "Eucalyptus"
    CloudStack = "CloudStack"
    CloudStack3 = "CloudStack3"


def _get_aws_metadata(conf, name):
    headers = {"Content-Type", "application/x-www-form-urlencoded",
               "Connection", "Keep-Alive",
               "Cache-Control", "no-cache"}

    url = conf.cloud_metadata_url + "/" + name
    req = urllib2.Request(url, headers=headers)

    response = urllib2.urlopen(req)
    if response.code != 200:
        return None
    html = response.read()
    return html.strip()


def _get_cloud_stack(conf, name):
    headers = {"Content-Type", "application/x-www-form-urlencoded",
               "Connection", "Keep-Alive",
               "Cache-Control", "no-cache"}

    output = util.run_script(conf, "getDhcpAddress")
    dhcp_server_address = output.strip()

    url = dhcp_server_address + "/" + name
    req = urllib2.Request(url, headers=headers)

    response = urllib2.urlopen(req)
    if response.code != 200:
        return None
    html = response.read().strip()

    if conf.cloud_name == CLOUD_TYPES.CloudStack:
        line_a = html.split("-")
        if len(line_a) > 2:
            return line_a[2]
    return html


def get_instance_id(conf):
    if conf.cloud_name == CLOUD_TYPES.Amazon or\
        conf.cloud_name == CLOUD_TYPES.Eucalyptus:
            return _get_aws_metadata(conf, "instance-id")
    elif conf.cloud_name == CLOUD_TYPES.CloudStack:
        return _get_cloud_stack(conf, "latest/instance-id")
    elif conf.cloud_name == CLOUD_TYPES.CloudStack3:
        return _get_cloud_stack(conf, "latest/vm-id")
    else:
        return None
