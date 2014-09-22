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

import dcm.agent.jobs as jobs


class GetDockerHostInfo(jobs.Plugin):

    protocol_arguments = {
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetDockerHostInfo, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetDockerHostInfo(conf, job_id, items_map, name, arguments)
