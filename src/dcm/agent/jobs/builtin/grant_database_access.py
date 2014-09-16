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
import dcm.agent.exceptions as exceptions
import dcm.agent.utils as utils
import dcm.agent.jobs.direct_pass as direct_pass


class GrantDBAccess(direct_pass.DirectPass):

    protocol_arguments = {
        "customerId":
        ("Not currently used.",
         True, str, None),
        "serviceId":
        ("The installed service whose enstratus-dbgrant program will be "
         "called.",
         True, str, None),
        "configuration":
        ("The configuration information to be passed to the services "
         "enstratus-dbgrant program",
         True, utils.base64type_convertor, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GrantDBAccess, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        if self.conf.is_imaging():
            raise exceptions.AgentPluginOperationIsImagingException(
                operation_name=self.name)
        config_file = self.conf.get_temp_file("database.cfg")
        with open(config_file, "w") as fptr:
            fptr.write(self.args.configuration)
        try:
            self.ordered_param_list = [self.arguments["serviceId"],
                                       config_file]
            return super(GrantDBAccess, self).run()
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return GrantDBAccess(conf, job_id, items_map, name, arguments)
