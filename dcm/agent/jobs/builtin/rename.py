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
from dcm.agent import exceptions, cloudmetadata

import dcm.agent.jobs.direct_pass as direct_pass


_g_logger = logging.getLogger(__name__)


class Rename(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Rename, self).__init__(
            conf, job_id, items_map, name, arguments)

        try:
            self.ordered_param_list = [arguments["server_name"]]
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

    def run(self):
        private_ips = cloudmetadata.get_ipv4_addresses(self.conf)
        if not private_ips:
            reply_doc = {
                "return_code": 1,
                "message": "No IP Address was found"
            }
            return reply_doc

        _g_logger.debug("Acquired ip addr %s" % private_ips[0])
        self.ordered_param_list.extend(private_ips[0])

        return super(Rename, self).run()


def load_plugin(conf, job_id, items_map, name, arguments):
    return Rename(conf, job_id, items_map, name, arguments)
