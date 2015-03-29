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
import re
from dcm.agent import exceptions, utils

import dcm.agent.jobs.direct_pass as direct_pass


_g_logger = logging.getLogger(__name__)


def is_legal(proposed_name):
    regex = "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$"
    allowed = re.compile(regex)
    if allowed is None:
        raise exceptions.AgentPluginMessageException(
                "%s is an invalid hostname" % proposed_name)


class Rename(direct_pass.DirectPass):

    protocol_arguments = {
        "serverName":
        ("The host name to which this server will be set.",
         True, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Rename, self).__init__(
            conf, job_id, items_map, name, arguments)

        is_legal(arguments["serverName"])
        self.ordered_param_list = [arguments["serverName"]]

    def run(self):
        private_ips = self.conf.meta_data_object.get_ipv4_addresses(self.conf)
        if not private_ips:
            reply_doc = {
                "return_code": 1,
                "message": "No IP Address was found"
            }
            return reply_doc

        utils.log_to_dcm(logging.DEBUG, "Acquired ip addr %s" % private_ips[0])
        self.ordered_param_list.append(private_ips[0])

        return super(Rename, self).run()


def load_plugin(conf, job_id, items_map, name, arguments):
    return Rename(conf, job_id, items_map, name, arguments)
