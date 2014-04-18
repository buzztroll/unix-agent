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
from dcm.agent import exceptions
import dcm.agent.jobs.direct_pass as direct_pass


class RevokeDBAccess(direct_pass.DirectPass):

    protocol_arguments = {
        "serviceId":
            ("The ID of the service that will have its rights revoked.",
             True, str),
        "configurationData":
            ("The configuration data that will be written to a file and "
             "passed into the revokeDatabaseAccess script",
             True, str)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RevokeDBAccess, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        if self.conf.is_imaging():
            raise exceptions.AgentPluginOperationIsImagingException(
                operation_name=self.name)
        config_file = self.conf.get_temp_file("database.cfg")
        with open(config_file, "w") as fptr:
            fptr.write(self.arguments["configurationData"].decode("utf-8"))
        try:
            self.ordered_param_list = [self.arguments["serviceId"],
                                       config_file]
            return super(RevokeDBAccess, self).run()
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return RevokeDBAccess(conf, job_id, items_map, name, arguments)
