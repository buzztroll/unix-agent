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
import dcm.agent.jobs.direct_pass as direct_pass


class RevokeDBAccess(direct_pass.DirectPass):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RevokeDBAccess, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        # TODO do not allow if imaging
        config_file = self.conf.get_temp_file("database.cfg")
        with open(config_file, "w") as fptr:
            fptr.write(self.arguments["configurationData"])
        try:
            self.ordered_param_list = [self.arguments[""],
                                       config_file]
            return super(RevokeDBAccess, self).run()
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return RevokeDBAccess(conf, job_id, items_map, name, arguments)
