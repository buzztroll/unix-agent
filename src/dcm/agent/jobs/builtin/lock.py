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


class Lock(jobs.Plugin):

    protocol_arguments = {
        "timeout": ("The number of milliseconds to wait to get the lock",
                    True, long, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Lock, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        timeout = self.args.timeout
        if timeout < 10000:
            timeout = 10000
        self.conf.jr.lock(timeout, False)
        reply_doc = {
            "return_code": 0,
            "reply_type": "void"
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return Lock(conf, job_id, items_map, name, arguments)
