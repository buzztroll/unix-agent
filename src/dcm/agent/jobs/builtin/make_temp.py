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
from dcm.agent import exceptions

import dcm.agent.jobs.direct_pass as direct_pass


class MakeTemp(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(MakeTemp, self).__init__(
            conf, job_id, items_map, name, arguments)
        self.ordered_param_list = []


def load_plugin(conf, job_id, items_map, name, arguments):
    return MakeTemp(conf, job_id, items_map, name, arguments)
