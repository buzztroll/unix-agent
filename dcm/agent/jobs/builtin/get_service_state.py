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

import dcm.agent.jobs as jobs
import dcm.agent.utils as utils


class GetServiceState(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetServiceState, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name),
                        arguments["serviceId"]]

    def call(self):
        (stdout, stderr, rc) = utils.run_command(self.command)
        if rc != 0:
            reply_doc = {
                "return_code": rc,
                "message": stderr
            }
            return reply_doc

        line = stdout.split(os.linesep)[0].strip()
        reply_doc = {
            "return_code": 0,
            "reply_type": "string",
            "reply_object": line
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetServiceState(conf, job_id, items_map, name, arguments)
