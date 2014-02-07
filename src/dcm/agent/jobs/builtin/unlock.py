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

# TODO FIGURE OUT LOCKS

import dcm.agent.jobs as jobs


class UnLock(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(UnLock, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name)]

    def run(self):
        self._conf.unlock()

        reply_doc = {
            "return_code": 0,
            "reply_type": "void"
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return UnLock(conf, job_id, items_map, name, arguments)
