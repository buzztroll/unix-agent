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
import os
import socket
from dcm.agent import cloudmetadata

import dcm.agent
import dcm.agent.cloudmetadata as cloud_instance


# This function does not really work
def _gather_ipv4_addresses():
    addrs = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    ipv4s = set([i[4][0] for i in addrs])
    # this turns the set into a list so that it can be JSON serialized
    return list(ipv4s)


def _gather_ipv6_addresses():
    addrs = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6)
    ipv6s = set([i[4][0] for i in addrs])
    # this turns the set into a list so that it can be JSON serialized
    return list(ipv6s)


def _get_agent_id(conf):
    if not conf.storage_idfile or not os.path.exists(conf.storage_idfile):
        return None

    with open(conf.storage_idfile, "r") as fptr:
        agent_id = fptr.readline().strip()
        return agent_id


def _get_injected_id():
    pass


def get_handshake(conf):
    if conf.test_skip_handshake:
        # TODO make this configurable from the test conf files
        return {
            'ipv4': ["127.0.0.1"],
            'ipv6': [],
            'agent_id': "test-agent",
            'vm_instance': "vdeadbeef",
            'injected_id': "ideadbeef",
            'version': dcm.agent.g_version,
            'protocol_version': dcm.agent.g_protocol_version,
            'platform': conf.platform_name
        }

    ipv4s = cloudmetadata.get_ipv4_addresses(conf)
    ipv6s = []
    injected_id = _get_injected_id()
    agent_id = _get_agent_id(conf)

    vm_instance = cloud_instance.get_instance_id(conf)

    handshake_doc = {
        'ipv4': ipv4s,
        'ipv6': ipv6s,
        'agent_id': agent_id,
        'vm_instance': vm_instance,
        'injected_id': injected_id,
        'version': dcm.agent.g_version,
        'protocol_version': dcm.agent.g_protocol_version,
        'platform': conf.platform_name
    }

    return handshake_doc
