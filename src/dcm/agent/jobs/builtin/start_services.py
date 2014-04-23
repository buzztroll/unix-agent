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

import dcm.agent.utils as utils
import dcm.agent.jobs as jobs


class StartServices(jobs.Plugin):

    protocol_arguments = {
        "serviceIds":
        ("The list of service IDs to start.",
         True, list)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StartServices, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.exe = conf.get_script_location(script_name)

    def run(self):
        service_list = self.arguments["serviceIds"]
        failures = []
        for service in service_list:
            command = [self.exe, service]
            try:
                cwd = self.conf.get_service_directory(service)
                (stdout, stderr, rc) = utils.run_command(
                    self.conf, command, cwd=cwd)
                if rc != 0:
                    failures.append(service + ":-1")
            except Exception as ex:
                failures.append(service + ":-1")
        reply_doc = {
            "return_code": 0,
            "reply_type": "string_array",
            "reply_object": failures
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return StartServices(conf, job_id, items_map, name, arguments)
