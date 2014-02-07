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


class GetServiceStates(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetServiceStates, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self._script_exe = conf.get_script_location(script_name)

    def run(self):
        string_list = []
        if self.conf.storage_services_dir and \
                not os.path.exists(self.conf.storage_services_dir):
            for f in os.listdir(self.conf.services_directory):
                if f[0] == "a" and os.path.isdir(
                        os.path.join(self.conf.services_directory, f)):
                    string_list.append(f)
                    try:
                        command = [self._script_exe, f]
                        (stdout, stderr, rc) = \
                            utils.run_command(self.conf, command)
                        line = stdout.split(os.linesep)[0].strip()
                        string_list.append(line)
                    except Exception as ex:
                        string_list.append("UNKNOWN: " + ex.message)

        reply_doc = {
            "return_code": 0,
            "reply_type": "string_array",
            "reply_object": string_list
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetServiceStates(conf, job_id, items_map, name, arguments)
