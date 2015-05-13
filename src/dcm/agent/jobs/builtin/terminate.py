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
import dcm.agent.jobs.direct_pass as direct_pass


class Terminate(direct_pass.DirectPass):

    protocol_arguments = {
        "ignoreErrors":
        ("Ignore any errors that are returned from the terminate script",
         False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Terminate, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = [self.args.ignoreErrors]


def load_plugin(conf, job_id, items_map, name, arguments):
    return Terminate(conf, job_id, items_map, name, arguments)
