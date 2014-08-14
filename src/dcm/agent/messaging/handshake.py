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
import os
from dcm.agent import cloudmetadata

import dcm.agent
import dcm.agent.cloudmetadata as cloud_instance


FOR_TEST_AGENT_ID_ENV = "FOR_TEST_AGENT_ID_ENV"


def get_handshake(conf):
    if conf.test_skip_handshake:
        # TODO make this configurable from the test conf files
        return {
            'ipv4': ["127.0.0.1"],
            'ipv6': [],
            'agent_id': "test-agent",
            'vm_instance': "vdeadbeef",
            'injected_id': "ideadbeef",
            'token': 'tdeadbeef',
            'version': dcm.agent.g_version,
            'protocol_version': dcm.agent.g_protocol_version,
            'platform': conf.platform_name
        }

    ipv4s = cloudmetadata.get_ipv4_addresses(conf)
    ipv6s = []
    injected_id = None
    agent_id = None
    if FOR_TEST_AGENT_ID_ENV in os.environ:
        agent_id = os.environ[FOR_TEST_AGENT_ID_ENV]

    vm_instance = conf.meta_data_object.get_instance_id()

    handshake_doc = {
        'ipv4': ipv4s,
        'ipv6': ipv6s,
        'agent_id': agent_id,
        'token': conf.token,
        'vm_instance': vm_instance,
        'injected_id': injected_id,
        'version': dcm.agent.g_version,
        'protocol_version': dcm.agent.g_protocol_version,
        'platform': conf.platform_name
    }

    return handshake_doc
