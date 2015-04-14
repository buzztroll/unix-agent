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

import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent import utils


_g_logger = logging.getLogger(__name__)


class GetPrivateIpAddress(direct_pass.DirectPass):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetPrivateIpAddress, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        _g_logger.debug("Running the handler %s" % __name__)

        private_ips = utils.get_ipv4_addresses()
        if not private_ips:
            reply_doc = {
                "return_code": 1,
                "message": "No IP Address was found"
            }
        else:
            reply_doc = {
                "return_code": 0,
                "reply_type": "string",
                "reply_object": private_ips[0]
            }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetPrivateIpAddress(conf, job_id, items_map, name, arguments)
